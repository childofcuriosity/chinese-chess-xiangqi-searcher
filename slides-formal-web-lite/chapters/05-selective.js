window.XQ_CHAPTERS = window.XQ_CHAPTERS || [];
window.XQ_CHAPTERS.push({
  "id": "05",
  "title": "Forward search: spending time on useful lines",
  "slides": [
    {
      "id": "a01",
      "title": "What can shallow search teach deeper search?",
      "eyebrow": "Stage 3 · The second half of search",
      "layout": "cards",
      "lead": "The previous iteration leaves a move, a score, and a likely principal variation to guide the next.",
      "cards": [
        {
          "title": "No guide move at this node",
          "text": "Find one cheaply before searching poor moves first."
        },
        {
          "title": "Candidates already ordered",
          "text": "Ask whether later moves can challenge the current best."
        },
        {
          "title": "Starting a new depth",
          "text": "Guess that the score remains near the previous iteration's result."
        }
      ],
      "steps": [
        "No guide move: first ask which move to search first.",
        "Ordered candidates: ask whether they beat the current best.",
        "New depth: ask whether the score is still nearby."
      ],
      "notes": "The previous iteration leaves a move, a score, and a likely principal variation to guide the next.\n\nNo guide move: first ask which move to search first.\n\nOrdered candidates: ask whether they beat the current best.\n\nNew depth: ask whether the score is still nearby.\n\nNo guide move at this node: Find one cheaply before searching poor moves first.\n\nCandidates already ordered: Ask whether later moves can challenge the current best.\n\nStarting a new depth: Guess that the score remains near the previous iteration's result.\n\nIdentify the question before naming the technique.",
      "sources": [
        "xiangqi_ai.cpp:1241",
        "xiangqi_ai.cpp:1411",
        "xiangqi_ai.cpp:1554"
      ],
      "takeaway": "Identify the question before naming the technique."
    },
    {
      "id": "a02",
      "title": "Without a guide, search shallowly to find one",
      "eyebrow": "Internal iterative deepening",
      "layout": "tree",
      "lead": "A deep node with no TT move may search poor moves first and delay useful alpha-beta bounds.",
      "tree": {
        "kind": "ordering",
        "root": "Depth 8: no TT best move",
        "branches": [
          {
            "label": "Search depth 4",
            "value": "Find guide move B"
          },
          {
            "label": "Reorder",
            "value": "B → A → C → D"
          },
          {
            "label": "Full-depth search",
            "value": "Start with B"
          }
        ]
      },
      "code": "if (!tt_move.is_valid() && depth >= 6) {\n  auto iid = shallow_search(depth - 4, alpha, beta);\n  tt_move = iid.move;       // For ordering\n}",
      "steps": [
        "At depth 8, there is no TT guide move.",
        "Search depth 4 and retain only best move B.",
        "Move B to the front, then search at the target depth.",
        "This is internal iterative deepening (IID)."
      ],
      "notes": "A deep node with no TT move may search poor moves first and delay useful alpha-beta bounds.\n\nAt depth 8, there is no TT guide move.\n\nSearch depth 4 and retain only best move B.\n\nMove B to the front, then search at the target depth.\n\nThis is internal iterative deepening (IID).\n\nIID produces a guide move, not the final score.",
      "sources": [
        "xiangqi_ai.cpp:1241-1247"
      ],
      "takeaway": "IID produces a guide move, not the final score."
    },
    {
      "id": "a03",
      "title": "Later moves challenge the current best",
      "eyebrow": "Principal variation search",
      "layout": "tree",
      "lead": "The first ordered move establishes a principal variation; later moves use an integer null window to challenge it.",
      "tree": {
        "kind": "alphabeta",
        "root": "Current best: α = 36",
        "branches": [
          {
            "label": "First move",
            "value": "Full window → 36"
          },
          {
            "label": "Second move",
            "value": "[36, 37] probe → does not exceed"
          },
          {
            "label": "Third move",
            "value": "[36, 37] probe → exceeds; re-search"
          }
        ]
      },
      "code": "first move: search(alpha, beta)\nlater move: search(alpha, alpha + 1)\nif (score > alpha && score < beta)\n    search(alpha, beta)      // Resolve a successful challenge",
      "steps": [
        "The first move has no reference, so use a full window.",
        "Later moves challenge the best with a null window.",
        "If they fail, we know they are not preferable.",
        "If they improve without cutting off, re-search with the full window.",
        "This is principal variation search (PVS)."
      ],
      "notes": "The first ordered move establishes a principal variation; later moves use an integer null window to challenge it.\n\nThe first move has no reference, so use a full window.\n\nLater moves challenge the best with a null window.\n\nIf they fail, we know they are not preferable.\n\nIf they improve without cutting off, re-search with the full window.\n\nThis is principal variation search (PVS).\n\nPVS probes narrowly and adds precision after a successful challenge.",
      "sources": [
        "xiangqi_ai.cpp:1410-1444"
      ],
      "takeaway": "PVS probes narrowly and adds precision after a successful challenge."
    },
    {
      "id": "a04",
      "title": "At a new depth, guess the score stays nearby",
      "eyebrow": "Aspiration window",
      "layout": "compare",
      "lead": "A narrow window around the previous result enables earlier cutoffs on both sides.",
      "cards": [
        {
          "title": "Previous iteration",
          "text": "Depth 6: score 120 (example)"
        },
        {
          "title": "Try a small window",
          "text": "Depth 7: search [90, 150]"
        },
        {
          "title": "Above the upper bound",
          "text": "Fail-high: widen the upper bound and re-search"
        },
        {
          "title": "Still outside",
          "text": "Keep widening; use the full window if needed"
        }
      ],
      "code": "delta = 30;\nalpha = prev_score - delta;\nbeta  = prev_score + delta;\nwhile (score <= alpha || score >= beta) {\n  widen_window();\n  if (delta > 1000) use_full_window();\n}",
      "steps": [
        "Depth 6 returned teaching score 120.",
        "Start the next depth with [90, 150].",
        "A result above the upper bound means the guess was too narrow.",
        "Widen and re-search, returning to a full window if needed.",
        "This is an aspiration window."
      ],
      "notes": "A narrow window around the previous result enables earlier cutoffs on both sides.\n\nDepth 6 returned teaching score 120.\n\nStart the next depth with [90, 150].\n\nA result above the upper bound means the guess was too narrow.\n\nWiden and re-search, returning to a full window if needed.\n\nThis is an aspiration window.\n\nPrevious iteration: Depth 6: score 120 (example)\n\nTry a small window: Depth 7: search [90, 150]\n\nAbove the upper bound: Fail-high: widen the upper bound and re-search\n\nStill outside: Keep widening; use the full window if needed\n\nAspiration guesses the iteration's score range and widens when wrong.",
      "sources": [
        "xiangqi_ai.cpp:1554-1583"
      ],
      "takeaway": "Aspiration guesses the iteration's score range and widens when wrong."
    },
    {
      "id": "a05",
      "title": "Three probes, three different questions",
      "eyebrow": "Distinguishing similar techniques",
      "layout": "table",
      "lead": "One finds an order, one challenges a best value, one predicts a score range.",
      "table": {
        "headers": [
          "Location",
          "Question",
          "Cheap action",
          "When to do more"
        ],
        "rows": [
          [
            "Deep node",
            "Which move goes first?",
            "IID shallow search for a guide",
            "Always follow with target-depth search"
          ],
          [
            "Later move at one node",
            "Can it beat the current best?",
            "PVS null-window probe",
            "Full-window re-search if inside the useful interval"
          ],
          [
            "New root depth",
            "Is the score near the previous one?",
            "Narrow aspiration window",
            "Widen after fail-low / fail-high"
          ]
        ]
      },
      "steps": [
        "IID finds a guide move.",
        "PVS challenges the current best.",
        "Aspiration predicts the new iteration's score range."
      ],
      "notes": "One finds an order, one challenges a best value, one predicts a score range.\n\nIID finds a guide move.\n\nPVS challenges the current best.\n\nAspiration predicts the new iteration's score range.\n\nUnderstand a technique by the question it answers.",
      "sources": [
        "xiangqi_ai.cpp:1241-1247",
        "xiangqi_ai.cpp:1411-1444",
        "xiangqi_ai.cpp:1554-1583"
      ],
      "takeaway": "Understand a technique by the question it answers."
    },
    {
      "id": "a06",
      "title": "Searching deeper requires accepting judgment risk",
      "eyebrow": "Selective search · Levels of risk",
      "layout": "cards",
      "lead": "Alpha-beta cuts off with sufficient bounds; the following heuristics can miss moves.",
      "cards": [
        {
          "title": "Level 1: reduce depth",
          "text": "Still search the candidate, initially at lower depth."
        },
        {
          "title": "Level 2: skip a move",
          "text": "Judge one candidate unlikely to be worth expanding."
        },
        {
          "title": "Level 3: skip the node",
          "text": "Return a bound without searching every candidate."
        }
      ],
      "steps": [
        "Reduced depth: the candidate is still searched.",
        "Skipped move: that candidate is not expanded.",
        "Skipped node: stop searching individual candidates.",
        "Greater savings bring greater costs when the judgment is wrong."
      ],
      "notes": "Alpha-beta cuts off with sufficient bounds; the following heuristics can miss moves.\n\nReduced depth: the candidate is still searched.\n\nSkipped move: that candidate is not expanded.\n\nSkipped node: stop searching individual candidates.\n\nGreater savings bring greater costs when the judgment is wrong.\n\nLevel 1: reduce depth: Still search the candidate, initially at lower depth.\n\nLevel 2: skip a move: Judge one candidate unlikely to be worth expanding.\n\nLevel 3: skip the node: Return a bound without searching every candidate.\n\nSelective search trades missed-move risk for deeper focused analysis.",
      "sources": [
        "xiangqi_ai.cpp:1177-1239",
        "xiangqi_ai.cpp:1337-1444"
      ],
      "takeaway": "Selective search trades missed-move risk for deeper focused analysis."
    },
    {
      "id": "a07",
      "title": "Reduce late quiet moves, but let them recover",
      "eyebrow": "Late move reductions (LMR)",
      "layout": "tree",
      "lead": "At sufficient depth, reduce late non-captures that do not give check and are not killers.",
      "tree": {
        "kind": "ordering",
        "root": "Original target depth 7",
        "branches": [
          {
            "label": "First move",
            "value": "Full child depth 6"
          },
          {
            "label": "Moves 2 and 3",
            "value": "Narrow window, usually unreduced"
          },
          {
            "label": "Ordinary quiet moves from 4 onward",
            "value": "Initially reduce by R plies"
          },
          {
            "label": "Unexpectedly beats the best",
            "value": "Restore depth, then full window if needed"
          }
        ]
      },
      "code": "if (late_quiet_move && !in_check && !gives_check) {\n  R = LMR_TABLE[depth][move_index]; // Initial depth reduction\n  R += history_is_bad; R -= history_is_good;\n  score = search(depth - 1 - R, narrow_window);\n  if (score challenges_best)\n    score = search(depth - 1, narrow_window);\n}",
      "steps": [
        "The first three moves establish a normal-depth reference.",
        "Later ordinary quiet moves initially get less depth.",
        "Good history reduces the reduction; poor history increases it.",
        "If the reduced result challenges the best, restore full depth.",
        "If it remains inside the useful window, re-search full-window."
      ],
      "notes": "At sufficient depth, reduce late non-captures that do not give check and are not killers.\n\nThe first three moves establish a normal-depth reference.\n\nLater ordinary quiet moves initially get less depth.\n\nGood history reduces the reduction; poor history increases it.\n\nIf the reduced result challenges the best, restore full depth.\n\nIf it remains inside the useful window, re-search full-window.\n\nLMR reduces first; underestimated candidates can recover full search.",
      "sources": [
        "xiangqi_ai.cpp:281-288",
        "xiangqi_ai.cpp:1395-1444"
      ],
      "takeaway": "LMR reduces first; underestimated candidates can recover full search."
    },
    {
      "id": "a08",
      "title": "At shallow depth, skip very late quiet moves",
      "eyebrow": "Late move pruning (LMP)",
      "layout": "cards",
      "lead": "After many higher-priority candidates at a shallow unchecked node, skip very late quiet moves.",
      "cards": [
        {
          "title": "Conditions",
          "text": "Non-root; depth ≤8; not in check; non-capture; not a killer."
        },
        {
          "title": "Count threshold",
          "text": "Tried candidates > 3 + depth²."
        },
        {
          "title": "Action",
          "text": "Skip directly to the next candidate without make or recursion."
        },
        {
          "title": "What may be missed",
          "text": "A late quiet move whose preparatory value appears later."
        }
      ],
      "steps": [
        "Search earlier high-priority moves normally.",
        "After 3 + depth² candidates, skip late ordinary quiet moves.",
        "This rule protects captures and killer moves.",
        "Risk: a late quiet move may be strong."
      ],
      "notes": "After many higher-priority candidates at a shallow unchecked node, skip very late quiet moves.\n\nSearch earlier high-priority moves normally.\n\nAfter 3 + depth² candidates, skip late ordinary quiet moves.\n\nThis rule protects captures and killer moves.\n\nRisk: a late quiet move may be strong.\n\nConditions: Non-root; depth ≤8; not in check; non-capture; not a killer.\n\nCount threshold: Tried candidates > 3 + depth².\n\nAction: Skip directly to the next candidate without make or recursion.\n\nWhat may be missed: A late quiet move whose preparatory value appears later.\n\nLMP skips late quiet moves using order and shallow-depth conditions.",
      "sources": [
        "xiangqi_ai.cpp:1337-1343"
      ],
      "takeaway": "LMP skips late quiet moves using order and shallow-depth conditions."
    },
    {
      "id": "a09",
      "title": "Even an optimistic margin cannot reach the threshold",
      "eyebrow": "Futility pruning",
      "layout": "compare",
      "lead": "The static score is too far from alpha/beta for an ordinary quiet move to change the conclusion within its margin.",
      "cards": [
        {
          "title": "Current static score",
          "text": "eval = 40 (example)"
        },
        {
          "title": "Shallow margin",
          "text": "100 + 100 × depth"
        },
        {
          "title": "Current threshold",
          "text": "alpha = 500 (example)"
        },
        {
          "title": "Decision",
          "text": "eval + margin ≤ alpha → skip this ordinary quiet move"
        }
      ],
      "code": "if (depth <= 6 && !in_check && !is_capture\n    && moves_count > 1) {\n  margin = 100 + 100 * depth;\n  if (eval + margin <= alpha) skip_move();\n}",
      "steps": [
        "The static score is far below alpha.",
        "Allow an optimistic margin of 100 + 100×depth.",
        "If it still cannot reach alpha, skip the move.",
        "Risk: static evaluation can underestimate delayed gains."
      ],
      "notes": "The static score is too far from alpha/beta for an ordinary quiet move to change the conclusion within its margin.\n\nThe static score is far below alpha.\n\nAllow an optimistic margin of 100 + 100×depth.\n\nIf it still cannot reach alpha, skip the move.\n\nRisk: static evaluation can underestimate delayed gains.\n\nCurrent static score: eval = 40 (example)\n\nShallow margin: 100 + 100 × depth\n\nCurrent threshold: alpha = 500 (example)\n\nDecision: eval + margin ≤ alpha → skip this ordinary quiet move\n\nFutility uses evaluation plus a margin to judge a quiet move's prospects.",
      "sources": [
        "xiangqi_ai.cpp:1345-1358"
      ],
      "takeaway": "Futility uses evaluation plus a margin to judge a quiet move's prospects."
    },
    {
      "id": "a10",
      "title": "Can SEE also prune main-search candidates?",
      "eyebrow": "From filtering and ordering to skipping",
      "layout": "board",
      "lead": "The rook-for-cannon exchange has SEE <0. Now consider the stronger action of skipping it entirely.",
      "boards": [
        {
          "fen": "4k4/9/9/2n6/c8/R8/4P4/9/9/4K4 w",
          "caption": "Red to move · Rook prepares to take the cannon at (4,0)",
          "orientation": "red",
          "highlights": [
            {
              "square": "a5",
              "kind": "from"
            },
            {
              "square": "a4",
              "kind": "capture"
            },
            {
              "square": "c3",
              "kind": "focus"
            }
          ],
          "arrows": [
            {
              "from": "a5",
              "to": "a4",
              "kind": "capture"
            }
          ],
          "annotations": [
            {
              "square": "c3",
              "text": "Horse can recapture"
            }
          ]
        },
        {
          "fen": "4k4/9/9/2n6/R8/9/4P4/9/9/4K4 b",
          "caption": "After rook capture · Black to move",
          "orientation": "red",
          "highlights": [
            {
              "square": "a4",
              "kind": "to"
            },
            {
              "square": "c3",
              "kind": "from"
            }
          ],
          "arrows": [
            {
              "from": "c3",
              "to": "a4",
              "kind": "capture"
            }
          ]
        },
        {
          "fen": "4k4/9/9/9/n8/9/4P4/9/9/4K4 w",
          "caption": "After horse recapture · Red rook removed",
          "orientation": "red",
          "highlights": [
            {
              "square": "a4",
              "kind": "to"
            }
          ],
          "annotations": [
            {
              "square": "a4",
              "text": "Net material −550"
            }
          ]
        }
      ],
      "steps": [
        "At first, rook takes cannon: teaching material gain +450.",
        "Horse (3,2) recaptures on (4,0), through empty leg (3,1).",
        "After two plies, net change is +450 −1000 = −550.",
        "This is a base-material ledger, not the full PST evaluate() score."
      ],
      "notes": "The rook-for-cannon exchange has SEE <0. Now consider the stronger action of skipping it entirely.\n\nAt first, rook takes cannon: teaching material gain +450.\n\nHorse (3,2) recaptures on (4,0), through empty leg (3,1).\n\nAfter two plies, net change is +450 −1000 = −550.\n\nThis is a base-material ledger, not the full PST evaluate() score.\n\nSEE supports filtering and ordering; SEE pruning skips main-search moves under restricted conditions.",
      "sources": [
        "象棋教学局面核验.md:B",
        "xiangqi_ai.cpp:91-106",
        "xiangqi_ai.cpp:931-1027"
      ],
      "takeaway": "SEE supports filtering and ordering; SEE pruning skips main-search moves under restricted conditions."
    },
    {
      "id": "a10b",
      "title": "An available capture may lose the exchange",
      "eyebrow": "Static exchange evaluation pruning",
      "layout": "cards",
      "lead": "At shallow unchecked nodes, skip expensive-piece captures with clearly losing target-square exchanges.",
      "cards": [
        {
          "title": "Check the shape",
          "text": "Depth ≤4; capture; not in check."
        },
        {
          "title": "Compare values",
          "text": "Victim value < attacker value."
        },
        {
          "title": "Simulate the exchange",
          "text": "SEE <−50 indicates a clear loss."
        },
        {
          "title": "Remaining risk",
          "text": "Sacrifices that draw the king, open lines, or create mate may have off-square compensation."
        }
      ],
      "code": "if (depth <= 4 && is_capture && !in_check) {\n  if (victim_value < attacker_value && see(move) < -50)\n    skip_move();\n}",
      "steps": [
        "First compare attacker and victim values.",
        "Then simulate alternating exchanges on the target square.",
        "Skip clearly losing captures with SEE <−50.",
        "Risk: the local ledger may miss global tactical compensation."
      ],
      "notes": "At shallow unchecked nodes, skip expensive-piece captures with clearly losing target-square exchanges.\n\nFirst compare attacker and victim values.\n\nThen simulate alternating exchanges on the target square.\n\nSkip clearly losing captures with SEE <−50.\n\nRisk: the local ledger may miss global tactical compensation.\n\nCheck the shape: Depth ≤4; capture; not in check.\n\nCompare values: Victim value < attacker value.\n\nSimulate the exchange: SEE <−50 indicates a clear loss.\n\nRemaining risk: Sacrifices that draw the king, open lines, or create mate may have off-square compensation.\n\nSEE pruning filters losing captures using the target-square exchange ledger.",
      "sources": [
        "xiangqi_ai.cpp:1362-1370",
        "xiangqi_ai.cpp:931-1027"
      ],
      "takeaway": "SEE pruning filters losing captures using the target-square exchange ledger."
    },
    {
      "id": "a11",
      "title": "Can we judge an entire node?",
      "eyebrow": "Whole-node heuristics",
      "layout": "cards",
      "lead": "Three questions: already good enough, apparently too poor, or still good after passing?",
      "cards": [
        {
          "title": "Already good enough?",
          "text": "Static evaluation minus a margin still exceeds beta."
        },
        {
          "title": "Too far behind?",
          "text": "QS verifies that the position still cannot reach alpha."
        },
        {
          "title": "Good even after a pass?",
          "text": "A hypothetical null move still exceeds the bound."
        }
      ],
      "steps": [
        "If static evaluation is already high, can we return a bound?",
        "If it is very low, can QS verify it cheaply?",
        "If passing still works, might a real move also suffice?",
        "Shared guards: non-root, not in check, away from mate-score ranges."
      ],
      "notes": "Three questions: already good enough, apparently too poor, or still good after passing?\n\nIf static evaluation is already high, can we return a bound?\n\nIf it is very low, can QS verify it cheaply?\n\nIf passing still works, might a real move also suffice?\n\nShared guards: non-root, not in check, away from mate-score ranges.\n\nAlready good enough?: Static evaluation minus a margin still exceeds beta.\n\nToo far behind?: QS verifies that the position still cannot reach alpha.\n\nGood even after a pass?: A hypothetical null move still exceeds the bound.\n\nWhole-node pruning saves the most and needs careful trigger conditions.",
      "sources": [
        "xiangqi_ai.cpp:1177-1239"
      ],
      "takeaway": "Whole-node pruning saves the most and needs careful trigger conditions."
    },
    {
      "id": "a12",
      "title": "Beyond the bound even after a margin",
      "eyebrow": "Reverse futility pruning (RFP)",
      "layout": "compare",
      "lead": "Futility asks whether one move can catch up; RFP asks whether a conservative static score can cut off the entire node.",
      "cards": [
        {
          "title": "MAX static score",
          "text": "eval"
        },
        {
          "title": "Conservative deduction",
          "text": "margin = 80 × depth"
        },
        {
          "title": "Still above beta",
          "text": "eval - margin ≥ beta"
        },
        {
          "title": "Return directly",
          "text": "Return a sufficient cutoff bound"
        }
      ],
      "code": "if (!is_root && depth <= 7 && !in_check) {\n  margin = 80 * depth;\n  if (eval - margin >= beta)\n    return eval - margin;\n}",
      "steps": [
        "The static score starts above beta.",
        "Subtract a conservative margin of 80×depth.",
        "If still above, return a node-level cutoff bound.",
        "Risk: a high static score can conceal forced counterplay."
      ],
      "notes": "Futility asks whether one move can catch up; RFP asks whether a conservative static score can cut off the entire node.\n\nThe static score starts above beta.\n\nSubtract a conservative margin of 80×depth.\n\nIf still above, return a node-level cutoff bound.\n\nRisk: a high static score can conceal forced counterplay.\n\nMAX static score: eval\n\nConservative deduction: margin = 80 × depth\n\nStill above beta: eval - margin ≥ beta\n\nReturn directly: Return a sufficient cutoff bound\n\nRFP cuts off when static advantage minus a margin still clears the bound.",
      "sources": [
        "xiangqi_ai.cpp:1177-1186"
      ],
      "takeaway": "RFP cuts off when static advantage minus a margin still clears the bound."
    },
    {
      "id": "a13",
      "title": "A very poor static score gets a tactical check",
      "eyebrow": "Razoring",
      "layout": "tree",
      "lead": "At a shallow node far below alpha, use QS first; return early only if immediate tactics cannot recover.",
      "tree": {
        "kind": "alphabeta",
        "root": "eval + 200×depth ≤ alpha",
        "branches": [
          {
            "label": "Abandon immediately?",
            "value": "Too risky"
          },
          {
            "label": "Run QS first",
            "value": "Check captures and evasions"
          },
          {
            "label": "QS still ≤alpha",
            "value": "Return this bound"
          },
          {
            "label": "QS improves",
            "value": "Continue normal search"
          }
        ]
      },
      "code": "if (depth <= 3 && !in_check\n    && eval + 200 * depth <= alpha) {\n  q = quiescence(alpha, beta);\n  if (q <= alpha) return q;\n}",
      "steps": [
        "Static evaluation plus a margin remains far below alpha.",
        "Use QS to check immediate captures and evasions.",
        "If QS cannot exceed alpha, return early.",
        "If QS improves, resume normal main search."
      ],
      "notes": "At a shallow node far below alpha, use QS first; return early only if immediate tactics cannot recover.\n\nStatic evaluation plus a margin remains far below alpha.\n\nUse QS to check immediate captures and evasions.\n\nIf QS cannot exceed alpha, return early.\n\nIf QS improves, resume normal main search.\n\nRazoring verifies a poor static position with QS before returning.",
      "sources": [
        "xiangqi_ai.cpp:1188-1199",
        "xiangqi_ai.cpp:1030-1118"
      ],
      "takeaway": "Razoring verifies a poor static position with QS before returning."
    },
    {
      "id": "a14b",
      "title": "Is the position good even if we pass?",
      "eyebrow": "Null move pruning (NMP)",
      "layout": "tree",
      "lead": "Temporarily switch turn and hash without moving a piece, run a reduced null-window search, then undo fully.",
      "tree": {
        "kind": "alphabeta",
        "root": "Current node: not in check, depth ≥3",
        "branches": [
          {
            "label": "Hypothetical pass",
            "value": "Switch turn, leave pieces in place"
          },
          {
            "label": "Reduced null window",
            "value": "Opponent still cannot pull the score back"
          },
          {
            "label": "Bound exceeded",
            "value": "Try a cutoff"
          },
          {
            "label": "Depth ≥10",
            "value": "Run a verification search"
          }
        ]
      },
      "code": "make_null_move();            // Search-only hypothesis\nR = reduced_plies(depth, eval); // Extra depth reduction\nscore = search(depth - 1 - R, narrow_window,\n               /* allow_null = */ false);\nundo_null_move();\nif (cutoff && depth >= 10)\n  verify_without_another_null();",
      "steps": [
        "Keep pieces fixed; switch only turn and its hash contribution.",
        "Use only at non-root unchecked nodes with at least three plies left.",
        "Disable another null move in the child search, preventing consecutive NMP.",
        "At depth ≥10, verify a cutoff with another reduced search.",
        "These guards reduce but do not eliminate endgame zugzwang errors."
      ],
      "notes": "Temporarily switch turn and hash without moving a piece, run a reduced null-window search, then undo fully.\n\nKeep pieces fixed; switch only turn and its hash contribution.\n\nUse only at non-root unchecked nodes with at least three plies left.\n\nDisable another null move in the child search, preventing consecutive NMP.\n\nAt depth ≥10, verify a cutoff with another reduced search.\n\nThese guards reduce but do not eliminate endgame zugzwang errors.\n\nZugzwang challenges the null-move assumption; depth guards and verification only reduce the risk.",
      "sources": [
        "xiangqi_ai.cpp:598-626",
        "xiangqi_ai.cpp:1201-1239"
      ],
      "takeaway": "Zugzwang challenges the null-move assumption; depth guards and verification only reduce the risk."
    },
    {
      "id": "a15",
      "title": "What if pruning misses the saving move?",
      "eyebrow": "Local two-pass search",
      "layout": "code",
      "lead": "The first pass allows three move-skipping rules. On either recovery trigger, restart the list with those rules disabled.",
      "code": "need_second_pass = near_losing_mate(best_score)\n                || (pruned_any && legal_searched == 0);\nfor (pass : {pruning_on, pruning_off_if_needed}) {\n  for (move : ordered_moves_from_beginning) {\n    if (pass == pruning_on)\n      maybe_skip_by_LMP_Futility_SEE();\n    search_normally(move); // May repeat searched moves\n  }\n}",
      "steps": [
        "First pass allows LMP, futility, and SEE pruning.",
        "Trigger 1: the best score remains near a losing mate.",
        "Trigger 2: candidates were pruned and no legal move was searched.",
        "Either trigger restarts the list with all three skipping rules disabled.",
        "Skipped moves get searched; some already searched moves are repeated."
      ],
      "notes": "The first pass allows three move-skipping rules. On either recovery trigger, restart the list with those rules disabled.\n\nFirst pass allows LMP, futility, and SEE pruning.\n\nTrigger 1: the best score remains near a losing mate.\n\nTrigger 2: candidates were pruned and no legal move was searched.\n\nEither trigger restarts the list with all three skipping rules disabled.\n\nSkipped moves get searched; some already searched moves are repeated.\n\nA second pass trades repeated work for a chance to recover missed moves.",
      "sources": [
        "xiangqi_ai.cpp:1310-1324",
        "xiangqi_ai.cpp:1337-1370",
        "xiangqi_ai.cpp:1512-1515"
      ],
      "takeaway": "A second pass trades repeated work for a chance to recover missed moves."
    },
    {
      "id": "a18",
      "title": "The naive approach: scan for blockers each time",
      "eyebrow": "Rook/cannon lines · Square-by-square baseline",
      "layout": "board",
      "lead": "For a cannon line, find the screen and then the next occupied square.",
      "boards": [
        {
          "fen": "3k5/9/4r4/9/9/4P4/9/4C4/9/4K4 w",
          "caption": "Red cannon (7,4): screen at (5,4), then black rook at (2,4)",
          "orientation": "red",
          "highlights": [
            {
              "square": "e7",
              "kind": "from"
            },
            {
              "square": "e5",
              "kind": "focus"
            },
            {
              "square": "e2",
              "kind": "capture"
            }
          ],
          "arrows": [
            {
              "from": "e7",
              "to": "e2",
              "kind": "capture"
            }
          ],
          "annotations": [
            {
              "square": "e5",
              "text": "Only screen"
            },
            {
              "square": "e2",
              "text": "Second piece"
            }
          ]
        }
      ],
      "code": "// Rule scan now runs in init_attack_tables\nnr = sr + d;\nwhile (inside(nr) && !occupied(nr)) {\n  moves |= 1 << nr; nr += d;       // Quiet moves before screen\n}\nif (inside(nr)) {                   // Found the screen\n  nr += d;\n  while (inside(nr) && !occupied(nr)) nr += d;\n  if (inside(nr)) moves |= 1 << nr; // Second piece can be captured\n}",
      "steps": [
        "Scan both directions from the source.",
        "Empty squares before the screen are legal quiet destinations.",
        "After the first piece, find the second as a capture target.",
        "The source still uses this rule, but only to build startup tables."
      ],
      "notes": "For a cannon line, find the screen and then the next occupied square.\n\nScan both directions from the source.\n\nEmpty squares before the screen are legal quiet destinations.\n\nAfter the first piece, find the second as a capture target.\n\nThe source still uses this rule, but only to build startup tables.\n\nWithout precomputation, each line query must locate both blockers at runtime.",
      "sources": [
        "象棋教学局面核验.md:C",
        "xiangqi_ai.cpp:228-246",
        "xiangqi_ai.cpp:258-273"
      ],
      "takeaway": "Without precomputation, each line query must locate both blockers at runtime."
    },
    {
      "id": "a18b",
      "title": "The real cost is repeated line queries",
      "eyebrow": "The hotspot is frequency, not ten squares",
      "layout": "cards",
      "lead": "A scan is short, but move generation, QS, and legality checking repeat it throughout search.",
      "cards": [
        {
          "title": "Main search",
          "text": "Each expanded position calls gen_all_moves, then gen_moves_for per piece."
        },
        {
          "title": "QS",
          "text": "QS still generates captures or evasions at normal-search leaves."
        },
        {
          "title": "Trial-move filtering",
          "text": "After each candidate, is_in_check queries the king's rank and file."
        },
        {
          "title": "Repeated input",
          "text": "Piece type + source index on the line + current 9/10-bit occupancy."
        }
      ],
      "code": "minimax position\n  └─ gen_all_moves(...)          // Main search / QS\n      └─ gen_moves_for(...)      // Each friendly piece\n\nFor every trial candidate\n  └─ make_move → is_in_check     // Query line attacks again",
      "steps": [
        "Main search generates candidates at each expanded position.",
        "QS continues generating tactical candidates after normal depth ends.",
        "Legality checks query rook/cannon attacks after trial moves.",
        "For line length L and k output moves, scanning costs O(L)+O(k)."
      ],
      "notes": "A scan is short, but move generation, QS, and legality checking repeat it throughout search.\n\nMain search generates candidates at each expanded position.\n\nQS continues generating tactical candidates after normal depth ends.\n\nLegality checks query rook/cannon attacks after trial moves.\n\nFor line length L and k output moves, scanning costs O(L)+O(k).\n\nMain search: Each expanded position calls gen_all_moves, then gen_moves_for per piece.\n\nQS: QS still generates captures or evasions at normal-search leaves.\n\nTrial-move filtering: After each candidate, is_in_check queries the king's rank and file.\n\nRepeated input: Piece type + source index on the line + current 9/10-bit occupancy.\n\nAt most ten squares is cheap once, expensive across many queries.",
      "sources": [
        "xiangqi_ai.cpp:772-824",
        "xiangqi_ai.cpp:1047-1073",
        "xiangqi_ai.cpp:1123-1129",
        "xiangqi_ai.cpp:1249-1250",
        "xiangqi_ai.cpp:1371-1383"
      ],
      "takeaway": "At most ten squares is cheap once, expensive across many queries."
    },
    {
      "id": "a18c",
      "title": "Scan at startup; look up during search",
      "eyebrow": "Precompute → Maintain → Query",
      "layout": "compare",
      "lead": "Precompute occupancy patterns once; moves update source/target bits, then integer occupancy selects a table entry.",
      "cards": [
        {
          "title": "1. Build at startup",
          "text": "Ranks: 9×512 inputs; files: 10×1024 inputs. Store separate rook and cannon masks."
        },
        {
          "title": "2. Make / undo",
          "text": "Update row_occ and col_occ at source/target; side_* tracks each side's occupancy."
        },
        {
          "title": "3. Query in search",
          "text": "TABLE[source][occ] returns the line mask; exclude friendly pieces and enumerate set bits."
        }
      ],
      "code": "// Startup: all source ranks and 10-bit occupancy patterns\nfor (int sr=0; sr<10; ++sr) for (int occ=0; occ<1024; ++occ)\n  CANNON_COL_ATT[sr][occ] = precompute(sr, occ);\n\n// Make / undo: update source and destination bits\ncol_occ[c2] |= 1 << r2;  col_occ[c1] &= ~(1 << r1);\n\n// Search: look up, exclude friendly pieces, enumerate bits\natt = CANNON_COL_ATT[r][col_occ[c]] & ~side_col_occ[side][c];\nwhile (att) { nr=__builtin_ctz(att); att&=att-1; ADDM(r,c,nr,c); }",
      "table": {
        "headers": [
          "This example's file query",
          "Integer / set bits",
          "Meaning"
        ],
        "rows": [
          [
            "col_occ[4]",
            "676 = {2,5,7,9}",
            "Black rook, screen, red cannon, and red king occupy the file"
          ],
          [
            "CANNON_COL_ATT[7][676]",
            "324 = {2,6,8}",
            "Capture (2,4); quiet moves to (6,4) and (8,4)"
          ],
          [
            "After excluding friendly pieces",
            "{2,6,8}",
            "All three targets remain"
          ]
        ]
      },
      "steps": [
        "At startup, enumerate sources and occupancies to build four tables.",
        "Initialization and make/undo maintain rank/file occupancy.",
        "One array lookup returns attacks; then exclude friendly pieces.",
        "ctz finds the lowest bit; mask&=mask−1 removes it; repeat for k moves."
      ],
      "notes": "Precompute occupancy patterns once; moves update source/target bits, then integer occupancy selects a table entry.\n\nAt startup, enumerate sources and occupancies to build four tables.\n\nInitialization and make/undo maintain rank/file occupancy.\n\nOne array lookup returns attacks; then exclude friendly pieces.\n\nctz finds the lowest bit; mask&=mask−1 removes it; repeat for k moves.\n\n1. Build at startup: Ranks: 9×512 inputs; files: 10×1024 inputs. Store separate rook and cannon masks.\n\n2. Make / undo: Update row_occ and col_occ at source/target; side_* tracks each side's occupancy.\n\n3. Query in search: TABLE[source][occ] returns the line mask; exclude friendly pieces and enumerate set bits.\n\nOccupancy selects a precomputed attack mask instead of rescanning blockers.",
      "sources": [
        "xiangqi_ai.cpp:210-279",
        "xiangqi_ai.cpp:316-320",
        "xiangqi_ai.cpp:444-473",
        "xiangqi_ai.cpp:485-604",
        "xiangqi_ai.cpp:669-711",
        "xiangqi_ai.cpp:1612-1616"
      ],
      "takeaway": "Occupancy selects a precomputed attack mask instead of rescanning blockers."
    },
    {
      "id": "a21b",
      "title": "Why did it choose that move?",
      "eyebrow": "Replay the whole reasoning chain",
      "layout": "cards",
      "lead": "The answer comes from a complete process that refines judgments within a time limit.",
      "cards": [
        {
          "title": "1 · Generate",
          "text": "Apply piece rules, then filter self-check after trial moves."
        },
        {
          "title": "2 · Order",
          "text": "TT, captures, killer, counter, and history prioritize candidates."
        },
        {
          "title": "3 · Search",
          "text": "Alternate choices; alpha-beta and PVS establish and challenge bounds."
        },
        {
          "title": "4 · Stabilize leaves",
          "text": "QS, SEE, and bounded check extensions handle unfinished tactics."
        },
        {
          "title": "5 · Allocate time",
          "text": "Reduce or skip selectively, with explicit missed-move risk."
        },
        {
          "title": "6 · Return on time",
          "text": "Return the best move from the last complete iteration."
        }
      ],
      "steps": [
        "Rules determine which candidates enter search.",
        "Ordering lets promising moves establish bounds early.",
        "Evaluation guides search; concrete replies refine static preferences.",
        "Selective search focuses the budget while accepting missed-move risk.",
        "At the deadline, return the last complete iteration."
      ],
      "notes": "The answer comes from a complete process that refines judgments within a time limit.\n\nRules determine which candidates enter search.\n\nOrdering lets promising moves establish bounds early.\n\nEvaluation guides search; concrete replies refine static preferences.\n\nSelective search focuses the budget while accepting missed-move risk.\n\nAt the deadline, return the last complete iteration.\n\n1 · Generate: Apply piece rules, then filter self-check after trial moves.\n\n2 · Order: TT, captures, killer, counter, and history prioritize candidates.\n\n3 · Search: Alternate choices; alpha-beta and PVS establish and challenge bounds.\n\n4 · Stabilize leaves: QS, SEE, and bounded check extensions handle unfinished tactics.\n\n5 · Allocate time: Reduce or skip selectively, with explicit missed-move risk.\n\n6 · Return on time: Return the best move from the last complete iteration.\n\nA move results from rules, memory, evaluation, and search working together.",
      "sources": [
        "xiangqi_ai.cpp:669-790",
        "xiangqi_ai.cpp:791-1118",
        "xiangqi_ai.cpp:1123-1542",
        "xiangqi_ai.cpp:1545-1605"
      ],
      "takeaway": "A move results from rules, memory, evaluation, and search working together."
    },
    {
      "id": "a22",
      "title": "From knowing nothing to a thinking Xiangqi system",
      "eyebrow": "Return to the three stages",
      "layout": "map",
      "currentChapter": 2,
      "lead": "Each practical problem adds a new capability.",
      "steps": [
        "Move: generate candidates and filter self-check.",
        "Evaluate: turn material and placement into comparable static signals.",
        "Search: consider replies and allocate time using memory, bounds, and heuristics."
      ],
      "notes": "Each practical problem adds a new capability.\n\nMove: generate candidates and filter self-check.\n\nEvaluate: turn material and placement into comparable static signals.\n\nSearch: consider replies and allocate time using memory, bounds, and heuristics.\n\nA Xiangqi engine organizes rules, memory, evaluation, and search into one system.",
      "sources": [
        "xiangqi_ai.cpp"
      ],
      "takeaway": "A Xiangqi engine organizes rules, memory, evaluation, and search into one system."
    }
  ]
});
