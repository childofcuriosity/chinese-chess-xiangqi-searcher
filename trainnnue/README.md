# NNUE: Features, Integer Evaluation, and Training

[简体中文](README_zh.md) · [Project overview](../README.md) · [Current results](../docs/nnue_g006_20261106/REPORT.md) · [Frozen recipe](../docs/nnue_g006_20261106/recipe.json)

The deployed g006 evaluator adds a learned residual to a material-and-piece-square score. It uses two views of a shared H128 feature table, clipped ReLU, and one of two scalar linear heads. Training uses 12 million positions labeled by the project's own search. Deployment uses feature scale **E20**, output scale **O128**, int8 feature weights and int16 feature accumulators.

## Coordinates, features, and shared parameters

The board has ten rows and nine columns. Row 0 is Black's home rank and row 9 is Red's. For a Red view, coordinates remain unchanged. For a Black view, rotate every square by 180 degrees: $(r,c)\mapsto(9-r,8-c)$. In both views, the friendly king then occupies the bottom palace.

Let the transformed friendly king occupy $(r_k,c_k)$. Its bucket is

$$
k=3(r_k-7)+(c_k-3),\qquad k\in\{0,\ldots,8\}.
$$

Piece type $t$ is numbered pawn, cannon, horse, elephant, advisor, rook, king as 0 through 6. Relative side $u$ is 0 for friendly and 1 for hostile. For a transformed piece square $q=9r+c$, the full feature index is

$$
f=(14k+2t+u)90+q.
$$

This defines 11,340 rows. Each piece, including either king, activates one row in each view. Both views use the same table $W\in\mathbb R^{11340\times128}$ and bias $b\in\mathbb R^{128}$.

Training shares the three side-king pairs by mapping buckets $2\to0$, $5\to3$, and $8\to6$, while also mirroring the piece column $c\to8-c$. Equivalently,

$$
W_{k_{\rm right},t,u,r,c}=W_{k_{\rm left},t,u,r,8-c}.
$$

Buckets 1, 4 and 7 retain all 90 independent piece locations. Thus there are $6\times14\times90=7560$ trainable 128-dimensional vectors. This mapping operates on feature indices. Export expands them into 11,340 rows, and runtime indexing needs no extra mirror operation. A separate 50% horizontal-mirror augmentation applies to training samples, including samples with center-file kings.

## Floating-point evaluation

Let $F_v(B)$ contain the active features for view $v$. Its accumulator is

$$
a_v=b+\sum_{f\in F_v(B)}W_f.
$$

Use $s$ for the side to move and $o$ for its opponent. The hidden activation is

$$
h=[\operatorname{clip}(a_s,0,1);\operatorname{clip}(a_o,0,1)]\in\mathbb R^{256}.
$$

With $n$ pieces on the board, including kings, choose phase $p=0$ for $n>20$ and $p=1$ otherwise. For output weights $v_p\in\mathbb R^{256}$ and bias $c_p$,

$$
z=v_p^{\mathsf T}h+c_p,\qquad r_{\rm float}=Kz,
\quad K=65.38910923790853.
$$

This is the complete floating architecture: feature addition, CReLU, and a phase-selected scalar linear output. Production inference computes only the selected head. Batched floating training and QAT compute both heads, then gather the head selected by each sample's phase. The scale $K$ converts normalized residual units to engine score units. It is fixed by the recipe.

The baseline $P_s$ includes material and positional bonuses. The neural residual is added to this full baseline. Native scores favor Red; define $\sigma=+1$ when Red moves and $-1$ when Black moves, so $P_s=\sigma P_{\rm red}$. The same conversion applies to teacher scores. Keeping this convention consistent is essential because the first half of $h$ always belongs to the player to move.

## Exact integer forward pass

Let $R$ round half-values away from zero. Deployment scales are $E=20$ for feature values and $O=128$ for output precision. Quantization produces

$$
\begin{aligned}
W_q&=\operatorname{clip}(R(EW),-128,127),\\
b_q&=\operatorname{clip}(R(Eb),-32768,32767),\\
v_q&=\operatorname{clip}(R(KO v),-32768,32767),\\
c_q&=\operatorname{clip}(R(KEO c),-2^{31},2^{31}-1).
\end{aligned}
$$

The integer evaluator then computes

$$
\begin{aligned}
A_v&=b_q+\sum_{f\in F_v(B)}W_{q,f},\\
H&=[\operatorname{clip}(A_s,0,E);\operatorname{clip}(A_o,0,E)],\\
Z&=c_{q,p}+\sum_{j=1}^{256}v_{q,p,j}H_j,\\
r&=\operatorname{clip}\left(R\left(\frac Z{EO}\right),-300,300\right),\\
V_s&=\operatorname{clip}(P_s+r,-19999,19999).
\end{aligned}
$$

Feature accumulators and activations are int16. Output weights are int16. The scale $K$ is already incorporated into the output integers, so native evaluation does not multiply by $K$ again. For example, $H_j=10$ at $E=20$ represents a floating activation of 0.5. Division by $EO$ restores the dot product to engine score units.

The compatible model file stores feature values in int16 slots and feature biases in int32 slots. The loader checks their ranges and builds the actual int8 feature arrays used by the search. File layout and runtime precision therefore describe different parts of the implementation.

### Selecting the feature scale and proving safety

After floating training, the exporter tests positive integers $E\le32767$. For each candidate, it first computes the un-clipped rounded values $\widetilde W=R(EW)$ and $\widetilde b=R(Eb)$. It selects the largest $E$ for which every $\widetilde W$ entry lies in $[-128,127]$ and every accumulator dimension satisfies

$$
|\widetilde b_j|+64\max_f|\widetilde W_{f,j}|\le32767.
$$

A final board has at most 32 pieces. The factor 64 additionally covers intermediate cache updates that can mix contributions from two boards, each with up to 32 pieces. CReLU occurs after accumulation, so its activation bound cannot protect an overflowing accumulator.

g006's floating feature range was approximately $[-4.855811,6.253492]$. Scale 21 exceeds the int8 range; scale 20 passes. After QAT, feature integers range from −98 to 125 and the largest verified accumulator bound is 8007.

For the output dot product, loading checks

$$
E\sum_j|v_{q,p,j}|\le2^{31}-1.
$$

This bounds partial sums as well as the complete product sum. AVX2 multiplies pairs of int16 values and adds their products into int32 lanes, then accumulates those lanes. g006's two head bounds are 11,148,860 and 10,063,220. The bias is added after conversion to int64. A wider accumulation fallback serves models that fail the fast-path bound.

### QAT uses the deployment computation

QAT starts from the selected floating checkpoint with $E$ fixed. Its forward pass applies the integer rounding, activation limits, residual limit and final score limit above. Floating master parameters receive gradients through straight-through rounding; integer division contributes the corresponding inverse-scale gradient, and clipping retains its clipping gradient. Exported predictions are checked against native C++ output.

Floating training fits $Kz$ directly. During QAT, the residual used by the loss is $V_s-P_s$, so final integer score clipping is included in the optimized prediction.

## Incremental evaluation and cache lifetimes

Making a move pushes a frame containing the moved piece, source, destination and captured piece. The frame has space and validity flags for two 128-dimensional accumulators. It initially records the change without reading feature vectors.

When evaluation requests a view, the engine finds a computed ancestor and applies the pending changes. With that view's king stationary,

$$
A'_v=A_v-W_{q,\rm source}+W_{q,\rm destination}-W_{q,\rm captured}.
$$

For a quiet move, omit the captured-piece term. If the parent is ready, one fused pass reads its accumulator, applies these changes and writes the child. For a longer unevaluated path, the first update fuses the ancestor copy with its change, and subsequent changes replay in order. Pruned branches that never request evaluation avoid accumulator updates.

When the viewing king moves, all feature indices for that view change. A refresh uses one of nine cache entries for that view. Each entry holds an accumulator and a 90-square board snapshot; differing squares remove their old contribution and add the current one. These caches are updated on refresh, rather than on every ordinary move. There are two views times nine king entries, each with a whole-board snapshot. The opposite view can update the moving king as an ordinary piece.

Undo restores the board and returns to the parent frame. It does not subtract the child's vector changes in reverse. Refresh caches keep their own snapshots and are compared against the requested board when used again. Loading a new position clears these caches and initializes the root frame.

## Data construction

For generation $g$, the current selected teacher plays PST and every selected NNUE, including itself. Every opponent contributes two million fresh valid positions. g006 uses g005 as teacher against PST and g001–g005, producing 12 million positions. The teacher labels both players' turns; each opponent supplies its own move choices.

Games begin with six uniformly random legal plies, which are excluded from sampling. Afterward, rank 1/2/3 is selected with probabilities 0.5/0.3/0.2, renormalized over available moves. PST searches at D4 and NNUE engines at D3. Games have at most 120 plies. Sampling occurs every two plies with alternated sampling phase and colors.

```text
for each opponent:
    play teacher versus opponent with alternating colors
    begin each game with 6 random legal plies
    at each subsequent position:
        sample desired move rank k
        S = teacher's independent full-window single-PV best score
        find the moving engine's best root move
        if k >= 2: exclude that move and search for the next
        if k == 3: exclude both preceding moves and search again
        record scheduled sample with S; play the kth move
    filter, deduplicate, and retain 2 million valid samples
```

On a teacher turn, its first-ranked move reuses the label search. Extra rank searches disable transposition-table writes and restore history, killer, counter-move and table-age state. The saved label is always the independent best score, even when exploration takes rank 2 or 3. No score-gap filter is applied.

The teacher configuration disables transposition-table score cutoffs, null-move pruning, late-move reductions, late-move pruning, futility pruning, razoring, reverse futility pruning, and static-exchange-evaluation filtering. It retains Principal Variation Search, check extensions, quiescence search and repetition rules. These settings define the fixed-depth search that produces each target.

Construction excludes positions in check and labels with absolute Red score at least 19999. The deduplication key is the 90-square board plus side to move. When duplicates have different labels, the pipeline retains a nonzero representative only when PST agrees and all nonzero search scores agree; otherwise it drops the conflict group. g006 had 19 search-score conflict groups: 10 retained by this rule and 9 discarded.

Teacher search carries the game's preceding history. That information is absent from NNUE features and the deduplication key, so labels need not be a unique function of the network input. Conflict handling does not remove this representation mismatch.

Game IDs assign complete games to 98% training, 1% validation and 1% calibration splits. Source, split and side-to-move quotas are then enforced before global mixing. g006 contains 11,760,000 training, 120,000 validation and 120,000 calibration positions, with equal Red/Black-to-move counts within each source and split. The calibration subset is unused for training, early stopping or scale selection.

## Loss, optimization, and candidate selection

For a saved teacher score $S_i$ and PST baseline $P_i$, both converted to side-to-move units, define

$$
d_i=\operatorname{clip}(S_i-P_i,-250,250),\qquad
L=\frac1N\sum_i\left(\frac{r_i-d_i}{K}\right)^2.
$$

Here $N$ is the batch size and $r_i$ the predicted residual. Only this residual MSE is optimized. Game results do not supply targets. For example, $S_i=180$, $P_i=100$ gives $d_i=80$; $S_i=500$, $P_i=100$ gives the clipped target 250. Both are arithmetic examples.

Each new model initializes feature vectors independently from $\mathcal N(0,0.01^2)$; feature biases, output weights and output biases start at zero. Training runs on a GTX 1650 Ti with AdamW, weight decay $10^{-6}$, effective batch size 8192 accumulated from four 2048-position microbatches, and gradient-norm clipping at 1. Training indices are shuffled each epoch; samples are mirrored horizontally with 50% probability.

| Setting | Floating training | Fixed-E QAT |
|---|---:|---:|
| Initial learning rate | 0.003 | 0.0003 |
| Maximum / minimum epochs | 150 / 25 | 30 / 5 |
| Early-stop patience | 15 | 8 |
| Minimum validation improvement | 0.00001 | 0.0000001 |
| Seed | 20261032 | 2026110191 |

Both stages use cosine scheduling with the stage's maximum epoch count as the period and 3% of initial learning rate as its floor. Validation residual MSE chooses the checkpoint, including epoch 0. Once the minimum epoch count is reached, the patience rule can terminate training.

| g006 model | Selected epoch / completed epochs | Validation residual MSE |
|---|---:|---:|
| Floating | 22 / 37 | 0.4918713882 |
| Direct integer quantization | — | 0.4975802947 |
| QAT integer export | 1 / 9 | 0.4886772009 |

These losses include division by $K^2$ and use the same 120,000-position validation set. Native integer validation output is checked against the QAT forward computation.

The exported model then plays 96 color-swapped opening pairs against every internal opponent. Nominal budgets are calibrated and frozen using actual search time; every matchup must have point-estimate score $(W+D/2)/N>0.5$ to promote the candidate. All scheduled matchups finish before expansion stops. This evaluates the complete deployed network inside search, complementing the label-fitting measurement.

## Results and available materials

The current model scored 83.07%, 76.56% and 57.03% against ElephantEye 3.1, Tianqi 1.1.8 and Cyclone 2007C. The [evaluation report](../docs/nnue_g006_20261106/REPORT.md) gives actual times, intervals, build differences and the approximately 2601 reference-Elo calculation. The [recipe](../docs/nnue_g006_20261106/recipe.json) and [pair evidence](../docs/nnue_g006_20261106/matches.compact.json) preserve settings and measurements.

The current production model can be used in the [online demonstration](http://164.152.167.211:8100). Matching production source, checkpoints, full datasets and the complete training package remain local; this document supplies their current computation and training specification.
