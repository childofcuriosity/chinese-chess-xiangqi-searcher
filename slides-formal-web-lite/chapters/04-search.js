window.XQ_CHAPTERS = window.XQ_CHAPTERS || [];
window.XQ_CHAPTERS.push({
  "id": "04",
  "title": "Forward search: reasoning through replies",
  "slides": [
    {
      "id": "s01",
      "title": "We can score positions, but cannot yet play",
      "eyebrow": "Stage 3 · Looking ahead",
      "layout": "map",
      "lead": "We have a board, rules, and evaluation. Now include the opponent's replies.",
      "cards": [
        {
          "title": "What we can do",
          "text": "Generate legal moves, make/undo, and evaluate leaves"
        },
        {
          "title": "What is missing",
          "text": "The opponent deliberately chooses replies that hurt us"
        },
        {
          "title": "This chapter",
          "text": "Understand counterplay within a limited time budget"
        }
      ],
      "steps": [
        "First, enumerate our candidates.",
        "Then add a layer: the opponent chooses too.",
        "Finally, face tree growth and deadlines."
      ],
      "notes": "We have a board, rules, and evaluation. Now include the opponent's replies.\n\nFirst, enumerate our candidates.\n\nThen add a layer: the opponent chooses too.\n\nFinally, face tree growth and deadlines.\n\nWhat we can do: Generate legal moves, make/undo, and evaluate leaves\n\nWhat is missing: The opponent deliberately chooses replies that hurt us\n\nThis chapter: Understand counterplay within a limited time budget\n\nSearch places evaluation inside alternating choices by both players.",
      "sources": [
        "xiangqi_ai.cpp:1123"
      ],
      "takeaway": "Search places evaluation inside alternating choices by both players."
    },
    {
      "id": "s02",
      "title": "The simplest approach: try every move",
      "eyebrow": "Enumeration · Make and undo",
      "layout": "board",
      "lead": "Generate → make → evaluate → undo → try the next move.",
      "boards": [
        {
          "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
          "caption": "Initial position: example Red candidates",
          "highlights": [
            {
              "square": "b9",
              "kind": "from"
            },
            {
              "square": "a7",
              "kind": "to"
            },
            {
              "square": "c7",
              "kind": "to"
            },
            {
              "square": "e6",
              "kind": "from"
            },
            {
              "square": "e5",
              "kind": "to"
            }
          ],
          "arrows": [
            {
              "from": "b9",
              "to": "a7",
              "kind": "move"
            },
            {
              "from": "b9",
              "to": "c7",
              "kind": "move"
            },
            {
              "from": "e6",
              "to": "e5",
              "kind": "move"
            }
          ],
          "annotations": []
        }
      ],
      "code": "best = -INF\nfor move in legal_moves:\n  captured = make(move)\n  score = evaluate()\n  undo(move, captured)\n  best = max(best, score)",
      "steps": [
        "Each candidate is a testable hypothesis.",
        "Evaluate after make.",
        "Return to the same position after undo."
      ],
      "notes": "Generate → make → evaluate → undo → try the next move.\n\nEach candidate is a testable hypothesis.\n\nEvaluate after make.\n\nReturn to the same position after undo.\n\nSearch begins by turning moves into reversible hypotheses.",
      "sources": [
        "xiangqi_ai.cpp:669",
        "xiangqi_ai.cpp:485",
        "xiangqi_ai.cpp:552"
      ],
      "takeaway": "Search begins by turning moves into reversible hypotheses."
    },
    {
      "id": "s03",
      "title": "One-ply evaluation is greedy",
      "eyebrow": "The first failure",
      "layout": "cards",
      "lead": "Winning material now does not mean the opponent cannot take it back.",
      "cards": [
        {
          "title": "The old logic",
          "text": "Choose whichever move leaves the highest immediate score."
        },
        {
          "title": "The reality",
          "text": "The opponent moves next and chooses our least welcome reply."
        },
        {
          "title": "The missing skill",
          "text": "Enumerate the opponent's replies after our own move."
        }
      ],
      "steps": [
        "We prefer a candidate with a higher immediate score.",
        "An opponent reply may reverse that advantage.",
        "At the next layer, the opponent chooses what is worst for us."
      ],
      "notes": "Winning material now does not mean the opponent cannot take it back.\n\nWe prefer a candidate with a higher immediate score.\n\nAn opponent reply may reverse that advantage.\n\nAt the next layer, the opponent chooses what is worst for us.\n\nThe old logic: Choose whichever move leaves the highest immediate score.\n\nThe reality: The opponent moves next and chooses our least welcome reply.\n\nThe missing skill: Enumerate the opponent's replies after our own move.\n\nThe opponent chooses the reply most unfavorable to us.",
      "sources": [
        "xiangqi_ai.cpp:1123"
      ],
      "takeaway": "The opponent chooses the reply most unfavorable to us."
    },
    {
      "id": "s04",
      "title": "One score perspective: Red maximizes, Black minimizes",
      "eyebrow": "Alternating choices · Minimax",
      "layout": "tree",
      "lead": "Scores always favor Red when positive: Red takes the maximum, Black the minimum.",
      "tree": {
        "kind": "minimax",
        "values": [
          4,
          -2,
          1,
          3
        ],
        "stage": 1,
        "caption": "4 / −2 / 1 / 3 are teaching values, not real game scores"
      },
      "steps": [
        "All four leaf values use Red's perspective.",
        "Black takes min(4,−2)=−2 and min(1,3)=1.",
        "Red takes max(−2,1)=1 at the root."
      ],
      "notes": "Scores always favor Red when positive: Red takes the maximum, Black the minimum.\n\nAll four leaf values use Red's perspective.\n\nBlack takes min(4,−2)=−2 and min(1,3)=1.\n\nRed takes max(−2,1)=1 at the root.\n\nMinimax encodes optimal opponent choice in recursion.",
      "sources": [
        "xiangqi_ai.cpp:1123",
        "xiangqi_ai.cpp:1409"
      ],
      "takeaway": "Minimax encodes optimal opponent choice in recursion."
    },
    {
      "id": "s05",
      "title": "Repeat the same logic at every layer",
      "eyebrow": "The recursive structure",
      "layout": "code",
      "lead": "Make, switch sides, search, undo; maximize and minimize alternate.",
      "code": "search(position, depth, red_turn):\n  if terminal: return win_or_loss_score(position)\n  if depth == 0: return evaluate(position)\n\n  best = red_turn ? -INF : +INF\n  for move in legal_moves:\n    captured = make(move)\n    score = search(position, depth - 1, !red_turn)\n    undo(move, captured)\n    best = red_turn ? max(best, score) : min(best, score)\n  return best",
      "steps": [
        "Stop at a terminal outcome or the depth limit.",
        "Make before recursion and undo afterward; switch the side to move.",
        "Red takes max; Black takes min."
      ],
      "notes": "Make, switch sides, search, undo; maximize and minimize alternate.\n\nStop at a terminal outcome or the depth limit.\n\nMake before recursion and undo afterward; switch the side to move.\n\nRed takes max; Black takes min.\n\nA game tree repeats make → switch sides → undo.",
      "sources": [
        "xiangqi_ai.cpp:1123",
        "xiangqi_ai.cpp:1371",
        "xiangqi_ai.cpp:1446"
      ],
      "takeaway": "A game tree repeats make → switch sides → undo."
    },
    {
      "id": "s17",
      "title": "Give checked positions a little more room",
      "eyebrow": "Check extension",
      "layout": "cards",
      "lead": "Extend one ply if the boundary cuts off a forced reply, with a bounded extension budget.",
      "cards": [
        {
          "title": "Why extend?",
          "text": "A checked side has forced replies; static evaluation may stop mid-sequence."
        },
        {
          "title": "How to limit it",
          "text": "Start with a depth-dependent budget and consume it on each extension."
        },
        {
          "title": "Scope",
          "text": "Limited extension reduces forced-line truncation but remains budgeted."
        }
      ],
      "steps": [
        "Depth reaches zero while the side is in check.",
        "With remaining budget, increase effective depth by one.",
        "Pass the reduced extension budget into recursion."
      ],
      "notes": "Extend one ply if the boundary cuts off a forced reply, with a bounded extension budget.\n\nDepth reaches zero while the side is in check.\n\nWith remaining budget, increase effective depth by one.\n\nPass the reduced extension budget into recursion.\n\nWhy extend?: A checked side has forced replies; static evaluation may stop mid-sequence.\n\nHow to limit it: Start with a depth-dependent budget and consume it on each extension.\n\nScope: Limited extension reduces forced-line truncation but remains budgeted.\n\nExtensions prioritize forcing lines while controlling total cost.",
      "sources": [
        "xiangqi_ai.cpp:1127",
        "xiangqi_ai.cpp:1148-1153",
        "xiangqi_ai.cpp:1412-1441"
      ],
      "takeaway": "Extensions prioritize forcing lines while controlling total cost."
    },
    {
      "id": "s22",
      "title": "What if depth eight is unfinished at the deadline?",
      "eyebrow": "Practical constraint · Time",
      "layout": "cards",
      "lead": "Time may expire after only some root candidates have been searched.",
      "cards": [
        {
          "title": "Fixed target",
          "text": "Starting directly at depth 8 may finish only the first few root moves."
        },
        {
          "title": "Interrupted state",
          "text": "Unsearched root moves prevent a complete comparison at this depth."
        },
        {
          "title": "A better target",
          "text": "Keep an answer from the latest fully completed depth at all times."
        }
      ],
      "steps": [
        "Depth 8 may time out before all root candidates are compared.",
        "Stop this iteration and retain the previous complete result.",
        "Complete depths in order so every interruption has an answer."
      ],
      "notes": "Time may expire after only some root candidates have been searched.\n\nDepth 8 may time out before all root candidates are compared.\n\nStop this iteration and retain the previous complete result.\n\nComplete depths in order so every interruption has an answer.\n\nFixed target: Starting directly at depth 8 may finish only the first few root moves.\n\nInterrupted state: Unsearched root moves prevent a complete comparison at this depth.\n\nA better target: Keep an answer from the latest fully completed depth at all times.\n\nTime management must decide what to return when the search is interrupted.",
      "sources": [
        "xiangqi_ai.cpp:1142-1147",
        "xiangqi_ai.cpp:1545-1603"
      ],
      "takeaway": "Time management must decide what to return when the search is interrupted."
    },
    {
      "id": "s23",
      "title": "Iterative deepening: save each completed answer",
      "eyebrow": "Meeting the deadline",
      "layout": "table",
      "lead": "Search depths 1, 2, 3…; on timeout return the latest completed iteration.",
      "table": {
        "headers": [
          "Depth",
          "Status",
          "Best move",
          "Score",
          "Action"
        ],
        "rows": [
          [
            "1",
            "Complete",
            "M1",
            "S1",
            "Save"
          ],
          [
            "2",
            "Complete",
            "M2",
            "S2",
            "Replace the previous complete answer"
          ],
          [
            "3",
            "Complete",
            "M3",
            "S3",
            "Replace the previous complete answer"
          ],
          [
            "4",
            "Timeout",
            "Incomplete",
            "Incomplete",
            "Discard this iteration; return M3"
          ]
        ]
      },
      "steps": [
        "Save the full result after depths 1, 2, and 3.",
        "Depth 4 times out midway and is not the final answer.",
        "Return the last complete result from depth 3.",
        "The previous best move improves ordering at the next depth."
      ],
      "notes": "Search depths 1, 2, 3…; on timeout return the latest completed iteration.\n\nSave the full result after depths 1, 2, and 3.\n\nDepth 4 times out midway and is not the final answer.\n\nReturn the last complete result from depth 3.\n\nThe previous best move improves ordering at the next depth.\n\nIterative deepening provides interruptibility and move-ordering experience.",
      "sources": [
        "xiangqi_ai.cpp:1545-1587"
      ],
      "takeaway": "Iterative deepening provides interruptibility and move-ordering experience."
    },
    {
      "id": "s24",
      "title": "Check the deadline every batch of nodes",
      "eyebrow": "Time control · Actual code",
      "layout": "code",
      "lead": "Check the hard deadline every 2048 nodes; after each iteration, decide whether to start another.",
      "code": "if ((nodes & 2047) == 0):\n  if elapsed > time_limit:\n    stop_search = true\n\nfor depth = 1..63:\n  result = search(depth)\n  if stop_search: break\n  last_res = result\n  if elapsed > max_time * 0.16 && depth >= 4:\n    break",
      "steps": [
        "Read the clock at the node-check interval.",
        "Propagate the timeout signal up the recursion.",
        "Update last_res only after a complete iteration.",
        "If one iteration uses over 16% of the total budget, do not start the larger next one."
      ],
      "notes": "Check the hard deadline every 2048 nodes; after each iteration, decide whether to start another.\n\nRead the clock at the node-check interval.\n\nPropagate the timeout signal up the recursion.\n\nUpdate last_res only after a complete iteration.\n\nIf one iteration uses over 16% of the total budget, do not start the larger next one.\n\nCheck time throughout search and retain the last complete result.",
      "sources": [
        "xiangqi_ai.cpp:1142-1147",
        "xiangqi_ai.cpp:1545-1603"
      ],
      "takeaway": "Check time throughout search and retain the last complete result."
    },
    {
      "id": "s07",
      "title": "Recursion makes the tree explode",
      "eyebrow": "New problem · Branching factor",
      "layout": "cards",
      "lead": "With b candidates and depth d, naive work grows roughly as b^d.",
      "cards": [
        {
          "title": "One more ply",
          "text": "Every existing leaf branches again."
        },
        {
          "title": "Leaves may be unstable",
          "text": "Later, captures may extend the search beyond the normal boundary."
        },
        {
          "title": "Teaching example",
          "text": "At 30 moves per position, depth 4 has about 810,000 leaves; depth 6 has 729 million."
        },
        {
          "title": "The real question",
          "text": "Do we need the exact score of every candidate?"
        }
      ],
      "steps": [
        "Each additional layer branches at every leaf.",
        "For b=30: b⁴=810000 and b⁶=729000000.",
        "Ask whether choosing the best move requires completing every branch."
      ],
      "notes": "With b candidates and depth d, naive work grows roughly as b^d.\n\nEach additional layer branches at every leaf.\n\nFor b=30: b⁴=810000 and b⁶=729000000.\n\nAsk whether choosing the best move requires completing every branch.\n\nOne more ply: Every existing leaf branches again.\n\nLeaves may be unstable: Later, captures may extend the search beyond the normal boundary.\n\nTeaching example: At 30 moves per position, depth 4 has about 810,000 leaves; depth 6 has 729 million.\n\nThe real question: Do we need the exact score of every candidate?\n\nExponential branching dominates the cost of individual evaluations.",
      "sources": [
        "xiangqi_ai.cpp:1123"
      ],
      "takeaway": "Exponential branching dominates the cost of individual evaluations."
    },
    {
      "id": "s07a",
      "title": "How do we accelerate the search?",
      "eyebrow": "Search roadmap · 1/2",
      "layout": "table",
      "lead": "Use bounds, stable leaves, position memory, and ordering to reach conclusions sooner.",
      "table": {
        "headers": [
          "Method",
          "Purpose"
        ],
        "rows": [
          [
            "Alpha-Beta",
            "Stop remaining branches when bounds already determine the choice"
          ],
          [
            "QS",
            "Continue tactical moves at leaves; generate all evasions when checked"
          ],
          [
            "SEE for QS filtering",
            "Filter clearly losing captures when not in check"
          ],
          [
            "Zobrist key",
            "Identify positions with a compact, incrementally updated fingerprint"
          ],
          [
            "TT lookup",
            "Use the key to locate previous search records"
          ],
          [
            "TT reuse",
            "Reuse sufficiently deep exact scores or bounds"
          ],
          [
            "TT replacement",
            "Retain valuable records within fixed capacity"
          ],
          [
            "TT move",
            "Try the cached best move first"
          ],
          [
            "Capture ordering + SEE",
            "Try more promising exchanges first"
          ],
          [
            "Killer",
            "Prioritize quiet moves that previously cut off at this ply"
          ],
          [
            "Counter",
            "Prioritize moves that successfully answered the previous move"
          ],
          [
            "History",
            "Order quiet moves by accumulated success"
          ]
        ]
      },
      "steps": [
        "Reduce branches needed to reach the same conclusion.",
        "Reuse searched positions and try promising moves earlier.",
        "SEE serves both QS filtering and capture ordering."
      ],
      "notes": "Use bounds, stable leaves, position memory, and ordering to reach conclusions sooner.\n\nReduce branches needed to reach the same conclusion.\n\nReuse searched positions and try promising moves earlier.\n\nSEE serves both QS filtering and capture ordering.\n\nAvoid redundant expansion and establish useful bounds earlier.",
      "sources": [
        "xiangqi_ai.cpp:863-1118",
        "xiangqi_ai.cpp:1123-1540"
      ],
      "takeaway": "Avoid redundant expansion and establish useful bounds earlier."
    },
    {
      "id": "s07b",
      "title": "Next: probe, reduce, recover, and look up",
      "eyebrow": "Search roadmap · 2/2",
      "layout": "table",
      "lead": "Cheap probes and selective search focus the budget; recovery and tables control costs.",
      "table": {
        "headers": [
          "Method",
          "Purpose"
        ],
        "rows": [
          [
            "IID",
            "Without a guide move, search shallowly to improve ordering"
          ],
          [
            "PVS",
            "Full window for the first move; narrow probes for others"
          ],
          [
            "Aspiration",
            "Start with a narrow window around the previous iteration's score"
          ],
          [
            "LMR",
            "Reduce depth for late, unpromising moves"
          ],
          [
            "LMP",
            "Skip very late quiet moves at shallow depth"
          ],
          [
            "Futility",
            "Skip shallow quiet moves whose optimistic estimate still falls short"
          ],
          [
            "SEE pruning",
            "Skip clearly losing exchanges at shallow depth"
          ],
          [
            "RFP",
            "Cut off when the static score clears the bound by a margin"
          ],
          [
            "Razoring",
            "Verify poor shallow positions with QS"
          ],
          [
            "NMP",
            "Probe a reduced-depth null move for an early cutoff"
          ],
          [
            "Second-pass recovery",
            "When triggered, rerun with three local skipping rules disabled"
          ],
          [
            "Rook/cannon attack tables",
            "Maintain occupancy incrementally and look up precomputed attacks"
          ]
        ]
      },
      "steps": [
        "Cheap probes ask whether full search is worthwhile.",
        "Selective methods focus the budget on likely critical branches.",
        "Recovery reduces missed-move risk; attack tables reduce repeated query cost."
      ],
      "notes": "Cheap probes and selective search focus the budget; recovery and tables control costs.\n\nCheap probes ask whether full search is worthwhile.\n\nSelective methods focus the budget on likely critical branches.\n\nRecovery reduces missed-move risk; attack tables reduce repeated query cost.\n\nSelective search focuses effort; recovery and tables control risk and per-query cost.",
      "sources": [
        "xiangqi_ai.cpp:1177-1540",
        "xiangqi_ai.cpp:210-279",
        "xiangqi_ai.cpp:485-604",
        "xiangqi_ai.cpp:669-711"
      ],
      "takeaway": "Selective search focuses effort; recovery and tables control risk and per-query cost."
    },
    {
      "id": "s08",
      "title": "First solve A: what will the opponent allow?",
      "eyebrow": "First cutoff · Establish a reference",
      "layout": "tree",
      "lead": "Red considers A; Black chooses the smaller of 3 and 5.",
      "tree": {
        "kind": "alphabeta",
        "values": [
          3,
          5,
          2,
          null,
          null
        ],
        "stage": 1,
        "caption": "3 / 5 / 2 are teaching values, not real game evaluations"
      },
      "steps": [
        "Black's first reply under A scores 3.",
        "The second scores 5.",
        "Black takes min(3,5)=3, giving Red an option worth 3."
      ],
      "notes": "Red considers A; Black chooses the smaller of 3 and 5.\n\nBlack's first reply under A scores 3.\n\nThe second scores 5.\n\nBlack takes min(3,5)=3, giving Red an option worth 3.\n\nSolve one path to establish a comparison bound.",
      "sources": [
        "xiangqi_ai.cpp:1451-1478"
      ],
      "takeaway": "Solve one path to establish a comparison bound."
    },
    {
      "id": "s09",
      "title": "B is unfinished. Do we already know enough?",
      "eyebrow": "First cutoff · Your decision",
      "layout": "tree",
      "lead": "B's first reply scores 2; a later reply might score 10. Continue?",
      "tree": {
        "kind": "alphabeta",
        "values": [
          3,
          5,
          2,
          null,
          null
        ],
        "stage": 2,
        "caption": "A=3 is known; B's MIN node has already seen 2"
      },
      "steps": [
        "The first opponent reply under B scores 2.",
        "Later replies remain unknown.",
        "Who chooses among B's replies?"
      ],
      "notes": "B's first reply scores 2; a later reply might score 10. Continue?\n\nThe first opponent reply under B scores 2.\n\nLater replies remain unknown.\n\nWho chooses among B's replies?\n\nA bound can justify stopping before all exact values are known.",
      "sources": [
        "xiangqi_ai.cpp:1451-1508"
      ],
      "takeaway": "A bound can justify stopping before all exact values are known."
    },
    {
      "id": "s10",
      "title": "We do not know B exactly, but will not choose it",
      "eyebrow": "New capability · Alpha-beta",
      "layout": "tree",
      "lead": "Red already has A=3; Black can hold Red to at most 2 under B.",
      "tree": {
        "kind": "alphabeta",
        "values": [
          3,
          5,
          2,
          null,
          null
        ],
        "stage": 3,
        "caption": "Skip the unknown branches: B's upper bound cannot challenge A"
      },
      "steps": [
        "The remaining B branches cannot change the root choice.",
        "B's exact score is still unknown.",
        "Alpha-beta uses bounds to decide when to stop."
      ],
      "notes": "Red already has A=3; Black can hold Red to at most 2 under B.\n\nThe remaining B branches cannot change the root choice.\n\nB's exact score is still unknown.\n\nAlpha-beta uses bounds to decide when to stop.\n\nWhen bounds determine the choice, exact values are unnecessary.",
      "sources": [
        "xiangqi_ai.cpp:1451-1508"
      ],
      "takeaway": "When bounds determine the choice, exact values are unnecessary."
    },
    {
      "id": "s10a",
      "title": "Alpha and beta are decision thresholds",
      "eyebrow": "From intuition to variables",
      "layout": "cards",
      "lead": "A MAX ancestor has an alternative worth at least alpha; a MIN ancestor has one worth at most beta.",
      "cards": [
        {
          "title": "Alpha: lower threshold",
          "text": "A MAX ancestor can get at least alpha elsewhere, so it rejects anything lower."
        },
        {
          "title": "Beta: upper threshold",
          "text": "A MIN ancestor can hold Red to at most beta elsewhere, so it rejects anything higher."
        },
        {
          "title": "The useful interval",
          "text": "Only a value between alpha and beta can change the ancestors' choices."
        }
      ],
      "steps": [
        "Alpha comes from MAX's existing alternatives.",
        "Beta comes from MIN's existing alternatives.",
        "Recursion passes both as the current search window."
      ],
      "notes": "A MAX ancestor has an alternative worth at least alpha; a MIN ancestor has one worth at most beta.\n\nAlpha comes from MAX's existing alternatives.\n\nBeta comes from MIN's existing alternatives.\n\nRecursion passes both as the current search window.\n\nAlpha: lower threshold: A MAX ancestor can get at least alpha elsewhere, so it rejects anything lower.\n\nBeta: upper threshold: A MIN ancestor can hold Red to at most beta elsewhere, so it rejects anything higher.\n\nThe useful interval: Only a value between alpha and beta can change the ancestors' choices.\n\nAlpha and beta record thresholds set by ancestor alternatives.",
      "sources": [
        "xiangqi_ai.cpp:1123",
        "xiangqi_ai.cpp:1451-1508"
      ],
      "takeaway": "Alpha and beta record thresholds set by ancestor alternatives."
    },
    {
      "id": "s10b",
      "title": "Translate A and B into alpha and beta",
      "eyebrow": "The same tree · Named variables",
      "layout": "tree",
      "lead": "A=3 sets alpha=3 at the root; B's first reply 2 lowers beta to 2.",
      "tree": {
        "kind": "alphabeta",
        "values": [
          3,
          5,
          2,
          null,
          null
        ],
        "stage": 3,
        "caption": "A=min(3,5)=3; B's MIN node first sees 2"
      },
      "code": "alpha = 3              // Root MAX already has A=3\nbeta = +INF            // Enter B's MIN node\n\nscore = 2              // First Black reply under B\nbeta = min(beta, score) // beta becomes 2\n\nif alpha >= beta:      // 3 >= 2\n  break                // Stop remaining B branches",
      "steps": [
        "A=min(3,5)=3 raises root alpha to 3.",
        "B's first reply makes beta=2; alpha≥beta, so skip both unknown branches."
      ],
      "notes": "A=3 sets alpha=3 at the root; B's first reply 2 lowers beta to 2.\n\nA=min(3,5)=3 raises root alpha to 3.\n\nB's first reply makes beta=2; alpha≥beta, so skip both unknown branches.\n\nWhen the bounds cross, this branch cannot affect the ancestor choice.",
      "sources": [
        "xiangqi_ai.cpp:1123",
        "xiangqi_ai.cpp:1451-1508"
      ],
      "takeaway": "When the bounds cross, this branch cannot affect the ancestor choice."
    },
    {
      "id": "s12",
      "title": "Depth runs out before the exchange ends",
      "eyebrow": "Horizon effect · Before the move",
      "layout": "board",
      "lead": "A fixed depth counts plies; it does not wait for captures and recaptures to finish.",
      "boards": [
        {
          "fen": "4k4/9/9/2n6/c8/R8/4P4/9/9/4K4 w",
          "caption": "Before: Red to move; the rook can capture the black cannon",
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
              "kind": "warning"
            },
            {
              "square": "b3",
              "kind": "leg"
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
              "square": "a5",
              "text": "Red rook"
            },
            {
              "square": "a4",
              "text": "Black cannon"
            },
            {
              "square": "c3",
              "text": "Black horse"
            }
          ]
        }
      ],
      "steps": [
        "Red's rook advances one square and captures the cannon.",
        "This move consumes the remaining normal depth.",
        "Black's horse can still recapture through the empty leg square (3,1)."
      ],
      "notes": "A fixed depth counts plies; it does not wait for captures and recaptures to finish.\n\nRed's rook advances one square and captures the cannon.\n\nThis move consumes the remaining normal depth.\n\nBlack's horse can still recapture through the empty leg square (3,1).\n\nA depth boundary is artificial; tactical exchanges need not end there.",
      "sources": [
        "xiangqi_ai.cpp:1151-1153"
      ],
      "takeaway": "A depth boundary is artificial; tactical exchanges need not end there."
    },
    {
      "id": "s13",
      "title": "Frame 1: the rook takes the cannon",
      "eyebrow": "Horizon effect · After capture",
      "layout": "compare",
      "lead": "Static evaluation records the captured cannon before the recapture enters the leaf score.",
      "boards": [
        {
          "fen": "4k4/9/9/2n6/c8/R8/4P4/9/9/4K4 w",
          "caption": "Before",
          "highlights": [
            {
              "square": "a5",
              "kind": "from"
            },
            {
              "square": "a4",
              "kind": "capture"
            }
          ],
          "arrows": [
            {
              "from": "a5",
              "to": "a4",
              "kind": "capture"
            }
          ],
          "annotations": []
        },
        {
          "fen": "4k4/9/9/2n6/R8/9/4P4/9/9/4K4 b",
          "caption": "After: (5,0) empty, red rook at (4,0), black cannon removed",
          "highlights": [
            {
              "square": "a4",
              "kind": "to"
            }
          ],
          "arrows": [],
          "annotations": []
        }
      ],
      "steps": [
        "The leaf temporarily contains one fewer black cannon.",
        "Static evaluation immediately reflects the material gain.",
        "Black's possible recapture determines whether that gain survives."
      ],
      "notes": "Static evaluation records the captured cannon before the recapture enters the leaf score.\n\nThe leaf temporarily contains one fewer black cannon.\n\nStatic evaluation immediately reflects the material gain.\n\nBlack's possible recapture determines whether that gain survives.\n\nA high post-capture score may be an unfinished-exchange illusion.",
      "sources": [
        "xiangqi_ai.cpp:434",
        "xiangqi_ai.cpp:1151-1153"
      ],
      "takeaway": "A high post-capture score may be an unfinished-exchange illusion."
    },
    {
      "id": "s14",
      "title": "Frame 2: the horse recaptures the rook",
      "eyebrow": "Horizon effect · Recapture",
      "layout": "compare",
      "lead": "The horse jumps through an empty leg square, removes the rook, and occupies its square.",
      "boards": [
        {
          "fen": "4k4/9/9/2n6/R8/9/4P4/9/9/4K4 b",
          "caption": "Before recapture: Black to move",
          "highlights": [
            {
              "square": "c3",
              "kind": "from"
            },
            {
              "square": "b3",
              "kind": "leg"
            },
            {
              "square": "a4",
              "kind": "capture"
            }
          ],
          "arrows": [
            {
              "from": "c3",
              "to": "a4",
              "kind": "capture"
            }
          ],
          "annotations": [
            {
              "square": "b3",
              "text": "Empty leg"
            }
          ]
        },
        {
          "fen": "4k4/9/9/9/n8/9/4P4/9/9/4K4 w",
          "caption": "After: (3,2) empty, black horse at (4,0), red rook removed",
          "highlights": [
            {
              "square": "a4",
              "kind": "to"
            }
          ],
          "arrows": [],
          "annotations": []
        }
      ],
      "steps": [
        "The empty leg allows the horse to recapture.",
        "The horse occupies the target and the rook disappears.",
        "Base material: Red gains cannon 450, loses rook 1000, net −550."
      ],
      "notes": "The horse jumps through an empty leg square, removes the rook, and occupies its square.\n\nThe empty leg allows the horse to recapture.\n\nThe horse occupies the target and the rook disappears.\n\nBase material: Red gains cannon 450, loses rook 1000, net −550.\n\nFollow captures and recaptures to a relatively stable position before evaluating.",
      "sources": [
        "xiangqi_ai.cpp:89-99",
        "xiangqi_ai.cpp:669",
        "xiangqi_ai.cpp:1030"
      ],
      "takeaway": "Follow captures and recaptures to a relatively stable position before evaluating."
    },
    {
      "id": "s14a",
      "title": "Why not deepen Minimax everywhere?",
      "eyebrow": "From full-width to selective extension",
      "layout": "compare",
      "lead": "Full-width deepening expands every legal move at every leaf; only unfinished tactical exchanges need attention here.",
      "cards": [
        {
          "title": "One extra full layer",
          "text": "All legal rook, horse, cannon, and pawn moves branch, including quiet ones."
        },
        {
          "title": "Two extra full layers",
          "text": "Every new node expands all candidates again, multiplying work."
        },
        {
          "title": "The exchange may still continue",
          "text": "A fixed extension merely moves the horizon; a longer exchange can cross it too."
        },
        {
          "title": "Selective continuation",
          "text": "After normal depth ends, continue captures and recaptures."
        }
      ],
      "steps": [
        "Full-width deepening expands quiet and tactical moves alike.",
        "A fixed extra depth can still stop mid-exchange.",
        "Concentrate extra work on unfinished exchanges, usually with fewer branches."
      ],
      "notes": "Full-width deepening expands every legal move at every leaf; only unfinished tactical exchanges need attention here.\n\nFull-width deepening expands quiet and tactical moves alike.\n\nA fixed extra depth can still stop mid-exchange.\n\nConcentrate extra work on unfinished exchanges, usually with fewer branches.\n\nOne extra full layer: All legal rook, horse, cannon, and pawn moves branch, including quiet ones.\n\nTwo extra full layers: Every new node expands all candidates again, multiplying work.\n\nThe exchange may still continue: A fixed extension merely moves the horizon; a longer exchange can cross it too.\n\nSelective continuation: After normal depth ends, continue captures and recaptures.\n\nSpend additional depth first on unfinished forcing lines.",
      "sources": [
        "xiangqi_ai.cpp:669",
        "xiangqi_ai.cpp:1030-1119"
      ],
      "takeaway": "Spend additional depth first on unfinished forcing lines."
    },
    {
      "id": "s15",
      "title": "At depth zero, QS takes over",
      "eyebrow": "Quiescence search · Entry",
      "layout": "board",
      "lead": "After the rook takes the cannon at normal depth zero, QS continues with Black to move.",
      "boards": [
        {
          "fen": "4k4/9/9/2n6/R8/9/4P4/9/9/4K4 b",
          "caption": "Normal depth=0 · Black to move",
          "highlights": [
            {
              "square": "c3",
              "kind": "from"
            },
            {
              "square": "a4",
              "kind": "capture"
            }
          ],
          "arrows": [
            {
              "from": "c3",
              "to": "a4",
              "kind": "capture"
            }
          ],
          "annotations": [
            {
              "square": "a4",
              "text": "Rook just captured cannon"
            },
            {
              "square": "c3",
              "text": "Horse can recapture"
            }
          ]
        }
      ],
      "code": "if (depth <= 0) {\n  return qs(alpha, beta, maximizingPlayer, 0);\n}",
      "steps": [
        "Normal search stops just after the rook capture.",
        "QS begins at qsDepth=0 and explores the horse recapture."
      ],
      "notes": "After the rook takes the cannon at normal depth zero, QS continues with Black to move.\n\nNormal search stops just after the rook capture.\n\nQS begins at qsDepth=0 and explores the horse recapture.\n\nQS is another recursive search entered at normal-search leaves.",
      "sources": [
        "xiangqi_ai.cpp:1148-1153"
      ],
      "takeaway": "QS is another recursive search entered at normal-search leaves."
    },
    {
      "id": "s15b",
      "title": "At each QS entry, choose candidates and stopping rules",
      "eyebrow": "Quiescence search · Entry decisions",
      "layout": "table",
      "lead": "Without check, tighten the window using stand pat; in check, find evasions; qsDepth bounds extra work.",
      "table": {
        "headers": [
          "Current state",
          "QS action"
        ],
        "rows": [
          [
            "Not in check",
            "Evaluate stand pat; if no cutoff, prepare captures"
          ],
          [
            "In check, qsDepth 0–3",
            "Skip stand pat; prepare all moves, then filter legal evasions"
          ],
          [
            "In check, qsDepth 4–6",
            "Check whether any legal evasion exists; evaluate if yes, return loss if none"
          ],
          [
            "qsDepth > 6",
            "Return evaluate() and stop QS"
          ]
        ]
      },
      "code": "qs(alpha, beta, maximizing, qsDepth):\n  inCheck = is_in_check(maximizing)\n  if !inCheck:\n    standPat = evaluate()\n    if maximizing:\n      if standPat >= beta: return beta\n      alpha = max(alpha, standPat)\n    else:\n      if standPat <= alpha: return alpha\n      beta = min(beta, standPat)\n\n  if qsDepth > 6: return evaluate()\n  if inCheck and qsDepth > 3:\n    if any legal evasion: return evaluate()\n    return maximizing ? -30000 + qsDepth\n                      :  30000 - qsDepth\n\n  moves = inCheck ? all_moves : captures",
      "notes": "Without check, tighten the window using stand pat; in check, find evasions; qsDepth bounds extra work.\n\nEntry logic establishes the baseline, candidate set, and depth boundary before recursion.",
      "sources": [
        "xiangqi_ai.cpp:1030-1090"
      ],
      "takeaway": "Entry logic establishes the baseline, candidate set, and depth boundary before recursion."
    },
    {
      "id": "s15a",
      "title": "For each candidate, make a move and call QS again",
      "eyebrow": "Quiescence search · Recursive loop",
      "layout": "code",
      "lead": "Make, reject illegal moves, recurse, undo, and update the node's window.",
      "code": "hasLegal = false\nfor m in moves:\n  captured = make(m)\n  if is_in_check(maximizing):\n    undo(m, captured); continue\n  hasLegal = true\n\n  score = qs(alpha, beta, !maximizing, qsDepth + 1)\n  undo(m, captured)\n\n  if maximizing:\n    if score >= beta: return beta\n    alpha = max(alpha, score)\n  else:\n    if score <= alpha: return alpha\n    beta = min(beta, score)\n\nif inCheck and !hasLegal:\n  return maximizing ? -30000 + qsDepth : 30000 - qsDepth\nreturn maximizing ? alpha : beta",
      "steps": [
        "For a legal move, call qs with the other side and qsDepth+1.",
        "After the child returns, undo and update alpha or beta.",
        "In check with no legal evasion, return the moving side's loss score."
      ],
      "notes": "Make, reject illegal moves, recurse, undo, and update the node's window.\n\nFor a legal move, call qs with the other side and qsDepth+1.\n\nAfter the child returns, undo and update alpha or beta.\n\nIn check with no legal evasion, return the moving side's loss score.\n\nQS recursion follows exchanges; hasLegal handles check with no escape.",
      "sources": [
        "xiangqi_ai.cpp:1091-1119"
      ],
      "takeaway": "QS recursion follows exchanges; hasLegal handles check with no escape."
    },
    {
      "id": "s16",
      "title": "SEE: cheaper and coarser than QS",
      "eyebrow": "Static exchange evaluation · SEE",
      "layout": "compare",
      "lead": "Estimate exchanges on one target square for QS filtering, main-search ordering, and shallow pruning.",
      "boards": [
        {
          "fen": "4k4/9/9/2n6/c8/R8/4P4/9/9/4K4 w",
          "caption": "Rook 900 takes cannon 400; horse recaptures: SEE = −500",
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
          "fen": "4k4/9/9/9/c8/R8/4P4/9/9/4K4 w",
          "caption": "Rook 900 takes cannon 400; no recapture: SEE = +400",
          "orientation": "red",
          "highlights": [
            {
              "square": "a5",
              "kind": "from"
            },
            {
              "square": "a4",
              "kind": "capture"
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
              "text": "Recapturer removed"
            }
          ]
        }
      ],
      "code": "SEE(move):\n  Fix the initial capture's target square\n  Alternate least-valuable attackers\n  Back up net gains from the end\n\nDo not expand replies away from the target square",
      "steps": [
        "SEE estimates alternating captures on one target instead of a full game tree.",
        "It is cheaper than QS but misses tactics elsewhere on the board.",
        "Both positions start with the same rook taking the same cannon.",
        "The horse recapture alone changes +400 to −500."
      ],
      "notes": "Estimate exchanges on one target square for QS filtering, main-search ordering, and shallow pruning.\n\nSEE estimates alternating captures on one target instead of a full game tree.\n\nIt is cheaper than QS but misses tactics elsewhere on the board.\n\nBoth positions start with the same rook taking the same cannon.\n\nThe horse recapture alone changes +400 to −500.\n\nSEE is a reusable local exchange estimate, not a complete search.",
      "sources": [
        "象棋教学局面核验.md:B",
        "xiangqi_ai.cpp:874-1027",
        "xiangqi_ai.cpp:1071-1082"
      ],
      "takeaway": "SEE is a reusable local exchange estimate, not a complete search."
    },
    {
      "id": "s16a",
      "title": "Turn a target-square exchange into numbers",
      "eyebrow": "SEE · Alternating least-valuable attackers",
      "layout": "code",
      "lead": "The separate SEE table uses rook 900, horse/cannon 400; it excludes PST and differs from earlier teaching values.",
      "code": "gain[0] = see_value(victim);       // Initial captured piece\non_sq = see_value(attacker);      // Piece now on target\nside = opponent;\n\nwhile ((an = attackers_to(target, side, occupancy)) > 0) {\n  best = least_valuable_attacker;\n  gain[n] = on_sq - gain[n - 1];\n  on_sq = see_value(best.piece);\n  remove best's source from occupancy; // Reveal sliders\n  side = !side;\n}",
      "table": {
        "headers": [
          "Stage",
          "Least-valuable attacker",
          "Gain calculation",
          "Result"
        ],
        "rows": [
          [
            "Red rook takes cannon",
            "Red rook 900",
            "gain[0] = cannon value",
            "400"
          ],
          [
            "Black horse takes rook",
            "Black horse 400",
            "gain[1] = rook 900 − gain[0] 400",
            "500"
          ],
          [
            "No further attacker",
            "Exchange chain ends",
            "Begin backward propagation",
            "Pending"
          ]
        ]
      },
      "steps": [
        "victim is the initially captured piece; gain[0] stores its SEE value.",
        "on_sq stores the value currently occupying the target.",
        "attackers_to finds the side's attackers; choose the least valuable.",
        "Removing each attacker updates occupancy and reveals rook/cannon lines.",
        "This example produces raw gain = [400, 500]."
      ],
      "notes": "The separate SEE table uses rook 900, horse/cannon 400; it excludes PST and differs from earlier teaching values.\n\nvictim is the initially captured piece; gain[0] stores its SEE value.\n\non_sq stores the value currently occupying the target.\n\nattackers_to finds the side's attackers; choose the least valuable.\n\nRemoving each attacker updates occupancy and reveals rook/cannon lines.\n\nThis example produces raw gain = [400, 500].\n\nThe forward loop builds the exchange ledger and reveals new attacks as occupancy changes.",
      "sources": [
        "xiangqi_ai.cpp:874-1008"
      ],
      "takeaway": "The forward loop builds the exchange ledger and reveals new attacks as occupancy changes."
    },
    {
      "id": "s16b",
      "title": "Either side can stop: back up from the end",
      "eyebrow": "SEE · Net gain and uses",
      "layout": "code",
      "lead": "A side stops an unfavorable continuation; the return value is the initiator's net gain or loss.",
      "code": "// Forward result: gain = [400, 500]\ngain[0] = -max(-gain[0], gain[1]);\n        = -max(-400, 500);\n        = -500;\n\nreturn gain[0];  // Net SEE of rook taking cannon",
      "table": {
        "headers": [
          "Use",
          "Condition",
          "Action for SEE = −500",
          "Purpose"
        ],
        "rows": [
          [
            "QS leaf filtering",
            "Not in check; valuable attacker takes cheaper victim; threshold 0",
            "Exclude from QS candidates",
            "Filtering: no QS recursion"
          ],
          [
            "Main-search capture ordering",
            "Valuable attacker takes cheaper victim; threshold 0",
            "Place in a lower ordering tier",
            "Ordering: still searched"
          ],
          [
            "Shallow main-search pruning",
            "Non-root, not in check, depth ≤4; threshold −50",
            "Skip on first pass",
            "Pruning: recover on specific second-pass conditions"
          ]
        ]
      },
      "steps": [
        "gain[1]=500 means Black benefits from the recapture and continues.",
        "Backward propagation changes the initial move's result to −500.",
        "SEE uses the initial capturer's perspective; negative means a net loss.",
        "One SEE value drives three different strengths of action."
      ],
      "notes": "A side stops an unfavorable continuation; the return value is the initiator's net gain or loss.\n\ngain[1]=500 means Black benefits from the recapture and continues.\n\nBackward propagation changes the initial move's result to −500.\n\nSEE uses the initial capturer's perspective; negative means a net loss.\n\nOne SEE value drives three different strengths of action.\n\nSEE returns the initiator's target-square exchange gain for filtering, ordering, and pruning.",
      "sources": [
        "xiangqi_ai.cpp:1009-1027",
        "xiangqi_ai.cpp:1071-1090",
        "xiangqi_ai.cpp:1277-1284",
        "xiangqi_ai.cpp:1362-1370"
      ],
      "takeaway": "SEE returns the initiator's target-square exchange gain for filtering, ordering, and pruning."
    },
    {
      "id": "m08",
      "title": "Two move orders reach the same position",
      "eyebrow": "Repeated work in search",
      "layout": "compare",
      "lead": "Both paths start from the initial position; reversing horse-development order reaches the same board and turn after four plies.",
      "boards": [
        {
          "fen": "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/9/P1P1P1P1P/1CN3NC1/9/R1BAKAB1R",
          "caption": "Path A endpoint · Red to move",
          "highlights": [
            {
              "square": "c2",
              "kind": "to"
            },
            {
              "square": "g2",
              "kind": "to"
            },
            {
              "square": "c7",
              "kind": "to"
            },
            {
              "square": "g7",
              "kind": "to"
            }
          ]
        },
        {
          "fen": "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/9/P1P1P1P1P/1CN3NC1/9/R1BAKAB1R",
          "caption": "Path B endpoint · Red to move",
          "highlights": [
            {
              "square": "c2",
              "kind": "to"
            },
            {
              "square": "g2",
              "kind": "to"
            },
            {
              "square": "c7",
              "kind": "to"
            },
            {
              "square": "g7",
              "kind": "to"
            }
          ]
        }
      ],
      "cards": [
        {
          "title": "Path A",
          "text": "Red left horse → Black left horse → Red right horse → Black right horse"
        },
        {
          "title": "Path B",
          "text": "Red right horse → Black right horse → Red left horse → Black left horse"
        },
        {
          "title": "Convergence",
          "text": "The same four horse squares and Red to move"
        }
      ],
      "steps": [
        "Path A develops the horses on the diagram's left first.",
        "Path B develops the horses on the right first.",
        "Identical endpoint states have identical continuation trees."
      ],
      "notes": "Both paths start from the initial position; reversing horse-development order reaches the same board and turn after four plies.\n\nPath A develops the horses on the diagram's left first.\n\nPath B develops the horses on the right first.\n\nIdentical endpoint states have identical continuation trees.\n\nPath A: Red left horse → Black left horse → Red right horse → Black right horse\n\nPath B: Red right horse → Black right horse → Red left horse → Black left horse\n\nConvergence: The same four horse squares and Red to move\n\nCaching avoids a duplicate subtree when move orders converge.",
      "sources": [
        "xiangqi_ai.cpp:201",
        "xiangqi_ai.cpp:444"
      ],
      "takeaway": "Caching avoids a duplicate subtree when move orders converge."
    },
    {
      "id": "m02",
      "title": "Can we avoid scanning 90 squares at every node?",
      "eyebrow": "Position identity · Update cost",
      "layout": "compare",
      "lead": "Square-by-square comparison recognizes positions, but repeatedly scanning the whole board adds cost.",
      "boards": [
        {
          "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR",
          "caption": "Current position · Red to move",
          "annotations": [
            {
              "square": "a0",
              "text": "Start here"
            },
            {
              "square": "i9",
              "text": "Compare through here"
            }
          ]
        }
      ],
      "cards": [
        {
          "title": "State identity",
          "text": "Pieces on 90 intersections plus side to move"
        },
        {
          "title": "Naive comparison",
          "text": "Inspect up to 90 squares each time"
        },
        {
          "title": "What we want",
          "text": "Update only what actually changes during a move"
        }
      ],
      "steps": [
        "The naive approach records and compares every square.",
        "A move usually changes only a few events.",
        "Maintain a compact fingerprint of the complete position."
      ],
      "notes": "Square-by-square comparison recognizes positions, but repeatedly scanning the whole board adds cost.\n\nThe naive approach records and compares every square.\n\nA move usually changes only a few events.\n\nMaintain a compact fingerprint of the complete position.\n\nState identity: Pieces on 90 intersections plus side to move\n\nNaive comparison: Inspect up to 90 squares each time\n\nWhat we want: Update only what actually changes during a move\n\nA cache key must represent the full state and update cheaply.",
      "sources": [
        "xiangqi_ai.cpp:444"
      ],
      "takeaway": "A cache key must represent the full state and update cheaply."
    },
    {
      "id": "m03",
      "title": "Give every piece-square event a random fingerprint",
      "eyebrow": "Zobrist hashing · Construction",
      "layout": "cards",
      "lead": "Assign a random 64-bit number to each piece-square combination, then combine active events.",
      "cards": [
        {
          "title": "Piece × Square",
          "text": "Z[red rook][(9,0)], Z[red horse][(9,1)], etc. are independent."
        },
        {
          "title": "Board fingerprint",
          "text": "H, called current_hash in code, XORs all active events."
        },
        {
          "title": "Side to move",
          "text": "XOR a TURN fingerprint when Black is to move."
        }
      ],
      "steps": [
        "Each piece-square combination gets an independent random number.",
        "XOR all current piece events together.",
        "Include TURN for Black to move."
      ],
      "notes": "Assign a random 64-bit number to each piece-square combination, then combine active events.\n\nEach piece-square combination gets an independent random number.\n\nXOR all current piece events together.\n\nInclude TURN for Black to move.\n\nPiece × Square: Z[red rook][(9,0)], Z[red horse][(9,1)], etc. are independent.\n\nBoard fingerprint: H, called current_hash in code, XORs all active events.\n\nSide to move: XOR a TURN fingerprint when Black is to move.\n\nA Zobrist key combines piece placement and side to move.",
      "sources": [
        "xiangqi_ai.cpp:201",
        "xiangqi_ai.cpp:444"
      ],
      "takeaway": "A Zobrist key combines piece placement and side to move."
    },
    {
      "id": "m04",
      "title": "Toggle the same fingerprint twice to restore it",
      "eyebrow": "Zobrist hashing · XOR",
      "layout": "code",
      "lead": "XOR acts as a toggle; applying it twice cancels it, and order does not matter.",
      "code": "H ^= X;   // Add event X\nH ^= X;   // Toggle again to remove X\n\nA ^ B ^ C == C ^ A ^ B",
      "steps": [
        "X ^ X = 0: the same event cancels itself.",
        "A ^ B ^ C = C ^ A ^ B: combination order does not matter.",
        "Undo repeats the same XOR operations to restore the old key."
      ],
      "notes": "XOR acts as a toggle; applying it twice cancels it, and order does not matter.\n\nX ^ X = 0: the same event cancels itself.\n\nA ^ B ^ C = C ^ A ^ B: combination order does not matter.\n\nUndo repeats the same XOR operations to restore the old key.\n\nAdd, remove, and undo all use the same XOR operation.",
      "sources": [
        "xiangqi_ai.cpp:500",
        "xiangqi_ai.cpp:567"
      ],
      "takeaway": "Add, remove, and undo all use the same XOR operation."
    },
    {
      "id": "m05",
      "title": "A horse move updates old square, new square, and turn",
      "eyebrow": "Zobrist hashing · Quiet move",
      "layout": "board",
      "lead": "A quiet move takes three XOR operations instead of a board scan.",
      "boards": [
        {
          "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR",
          "caption": "Before · Red to move",
          "highlights": [
            {
              "square": "b9",
              "kind": "from"
            },
            {
              "square": "c7",
              "kind": "to"
            }
          ],
          "arrows": [
            {
              "from": "b9",
              "to": "c7"
            }
          ],
          "annotations": [
            {
              "square": "b9",
              "text": "Old horse square"
            }
          ]
        },
        {
          "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1CN4C1/9/R1BAKABNR",
          "caption": "After · Black to move",
          "highlights": [
            {
              "square": "b9",
              "kind": "from"
            },
            {
              "square": "c7",
              "kind": "to"
            }
          ],
          "annotations": [
            {
              "square": "c7",
              "text": "New horse square"
            }
          ]
        }
      ],
      "steps": [
        "H ^= Z[red horse][(9,1)] removes the old square.",
        "H ^= Z[red horse][(7,2)] adds the new square.",
        "H ^= Z_TURN changes Red to move into Black to move."
      ],
      "notes": "A quiet move takes three XOR operations instead of a board scan.\n\nH ^= Z[red horse][(9,1)] removes the old square.\n\nH ^= Z[red horse][(7,2)] adds the new square.\n\nH ^= Z_TURN changes Red to move into Black to move.\n\nAn ordinary move replaces a board scan with three XORs.",
      "sources": [
        "xiangqi_ai.cpp:485",
        "xiangqi_ai.cpp:500"
      ],
      "takeaway": "An ordinary move replaces a board scan with three XORs."
    },
    {
      "id": "m06",
      "title": "A pawn capture also removes the victim",
      "eyebrow": "Zobrist hashing · Capture",
      "layout": "board",
      "lead": "Four changes: mover source, captured target piece, mover destination, and turn.",
      "boards": [
        {
          "fen": "5k3/9/9/9/4p4/4P4/9/9/9/3K5",
          "caption": "Before · Red to move",
          "highlights": [
            {
              "square": "e5",
              "kind": "from"
            },
            {
              "square": "e4",
              "kind": "capture"
            }
          ],
          "arrows": [
            {
              "from": "e5",
              "to": "e4"
            }
          ],
          "annotations": [
            {
              "square": "e4",
              "text": "Black pawn"
            }
          ]
        },
        {
          "fen": "5k3/9/9/9/4P4/9/9/9/9/3K5",
          "caption": "After · Black to move",
          "highlights": [
            {
              "square": "e5",
              "kind": "from"
            },
            {
              "square": "e4",
              "kind": "to"
            }
          ],
          "annotations": [
            {
              "square": "e4",
              "text": "Red pawn occupies target"
            }
          ]
        }
      ],
      "steps": [
        "H ^= Z[red pawn][(5,4)]; H ^= Z[black pawn][(4,4)]",
        "H ^= Z[red pawn][(4,4)]",
        "H ^= Z_TURN"
      ],
      "notes": "Four changes: mover source, captured target piece, mover destination, and turn.\n\nH ^= Z[red pawn][(5,4)]; H ^= Z[black pawn][(4,4)]\n\nH ^= Z[red pawn][(4,4)]\n\nH ^= Z_TURN\n\nCaptures also update only changed events.",
      "sources": [
        "xiangqi_ai.cpp:500",
        "xiangqi_ai.cpp:552"
      ],
      "takeaway": "Captures also update only changed events."
    },
    {
      "id": "m09",
      "title": "Every node now has a cheaply updated key",
      "eyebrow": "Zobrist hashing · Connecting to the cache",
      "layout": "cards",
      "lead": "current_hash summarizes the position in 64 bits; make/undo update only changed events.",
      "cards": [
        {
          "title": "Complete state",
          "text": "Piece-square events and side to move determine current_hash."
        },
        {
          "title": "Incremental maintenance",
          "text": "The same XOR toggles update and restore the fingerprint."
        },
        {
          "title": "Next question",
          "text": "After locating a record, when is its search evidence reusable?"
        }
      ],
      "steps": [
        "current_hash summarizes piece placement and turn.",
        "Make and undo update only changed events.",
        "Next, map the key into a fixed-capacity transposition table."
      ],
      "notes": "current_hash summarizes the position in 64 bits; make/undo update only changed events.\n\ncurrent_hash summarizes piece placement and turn.\n\nMake and undo update only changed events.\n\nNext, map the key into a fixed-capacity transposition table.\n\nComplete state: Piece-square events and side to move determine current_hash.\n\nIncremental maintenance: The same XOR toggles update and restore the fingerprint.\n\nNext question: After locating a record, when is its search evidence reusable?\n\nZobrist identifies positions; the TT stores search evidence.",
      "sources": [
        "xiangqi_ai.cpp:198",
        "xiangqi_ai.cpp:444",
        "xiangqi_ai.cpp:500",
        "xiangqi_ai.cpp:567"
      ],
      "takeaway": "Zobrist identifies positions; the TT stores search evidence."
    },
    {
      "id": "s18",
      "title": "Map the key to a fixed cache slot",
      "eyebrow": "Transposition table · Array indexing",
      "layout": "code",
      "lead": "Different paths can reach the same position; save previous search results for reuse.",
      "code": "TT_SIZE = 1 << 23          // 2^23 slots\nTT_MASK = TT_SIZE - 1      // Low 23 bits set\nindex = current_hash & TT_MASK\nentry = transposition_table[index]",
      "cards": [
        {
          "title": "Why an array?",
          "text": "Every node probes it; direct indexing has fixed cost."
        },
        {
          "title": "Why a mask?",
          "text": "Power-of-two capacity lets hash & (SIZE−1) select the low 23 bits."
        },
        {
          "title": "What is stored?",
          "text": "One position-search record per slot; fields follow next."
        }
      ],
      "steps": [
        "Avoid searching the same position's subtree from scratch.",
        "TT_SIZE=2^23 gives indices 0 through 2^23−1.",
        "TT_MASK=2^23−1 retains the hash's low 23 bits.",
        "current_hash & TT_MASK selects one slot."
      ],
      "notes": "Different paths can reach the same position; save previous search results for reuse.\n\nAvoid searching the same position's subtree from scratch.\n\nTT_SIZE=2^23 gives indices 0 through 2^23−1.\n\nTT_MASK=2^23−1 retains the hash's low 23 bits.\n\ncurrent_hash & TT_MASK selects one slot.\n\nWhy an array?: Every node probes it; direct indexing has fixed cost.\n\nWhy a mask?: Power-of-two capacity lets hash & (SIZE−1) select the low 23 bits.\n\nWhat is stored?: One position-search record per slot; fields follow next.\n\nA mask maps the 64-bit fingerprint into a fixed-size array.",
      "sources": [
        "xiangqi_ai.cpp:34-41",
        "xiangqi_ai.cpp:1156"
      ],
      "takeaway": "A mask maps the 64-bit fingerprint into a fixed-size array."
    },
    {
      "id": "s18c",
      "title": "A cache record must explain its evidence",
      "eyebrow": "TT · Fields and replacement",
      "layout": "table",
      "lead": "The index locates a slot; verify its full hash before deciding whether its result applies.",
      "table": {
        "headers": [
          "Field",
          "Question answered"
        ],
        "rows": [
          [
            "hash",
            "Does the slot belong to this 64-bit position key?"
          ],
          [
            "depth",
            "How deeply was this node searched?"
          ],
          [
            "score + flag",
            "Is the score exact, an upper bound, or a lower bound?"
          ],
          [
            "best_move",
            "Which move was most promising last time?"
          ],
          [
            "age",
            "Which root-search age produced this record?"
          ]
        ]
      },
      "cards": [
        {
          "title": "Replacing a slot",
          "text": "Replace if empty, same hash, old age, or the new record is at least as deep."
        },
        {
          "title": "Starting a new search",
          "text": "Increment tt_age so older root-search records can be replaced sooner."
        }
      ],
      "steps": [
        "hash checks identity; depth and flag describe the score evidence.",
        "best_move can improve ordering even when the score cannot be reused.",
        "age and depth guide replacement under fixed capacity."
      ],
      "notes": "The index locates a slot; verify its full hash before deciding whether its result applies.\n\nhash checks identity; depth and flag describe the score evidence.\n\nbest_move can improve ordering even when the score cannot be reused.\n\nage and depth guide replacement under fixed capacity.\n\nReplacing a slot: Replace if empty, same hash, old age, or the new record is at least as deep.\n\nStarting a new search: Increment tt_age so older root-search records can be replaced sooner.\n\nTT entries store evidence and the metadata needed to assess it.",
      "sources": [
        "xiangqi_ai.cpp:80-87",
        "xiangqi_ai.cpp:1521-1549"
      ],
      "takeaway": "TT entries store evidence and the metadata needed to assess it."
    },
    {
      "id": "s19",
      "title": "Does the cache store a value or a bound?",
      "eyebrow": "TT · EXACT / ALPHA / BETA",
      "layout": "compare",
      "lead": "Save the original entry window; reuse sufficiently deep bounds only when they cross the current threshold.",
      "cards": [
        {
          "title": "TT_EXACT",
          "text": "Original window [3,8], exact result 5: return 5 directly."
        },
        {
          "title": "TT_ALPHA: upper bound",
          "text": "Stored 2≤current alpha=3: this branch cannot reach MAX's threshold; stop."
        },
        {
          "title": "TT_BETA: lower bound",
          "text": "Stored 9≥current beta=8: MIN has a lower alternative; stop."
        },
        {
          "title": "Insufficient depth",
          "text": "Do not substitute a shallow score for deeper search; still try best_move first."
        }
      ],
      "steps": [
        "Return exact values directly.",
        "An upper bound cuts off only when it is no greater than alpha.",
        "A lower bound cuts off only when it is no less than beta.",
        "If depth or bounds are insufficient, best_move still improves ordering."
      ],
      "notes": "Save the original entry window; reuse sufficiently deep bounds only when they cross the current threshold.\n\nReturn exact values directly.\n\nAn upper bound cuts off only when it is no greater than alpha.\n\nA lower bound cuts off only when it is no less than beta.\n\nIf depth or bounds are insufficient, best_move still improves ordering.\n\nTT_EXACT: Original window [3,8], exact result 5: return 5 directly.\n\nTT_ALPHA: upper bound: Stored 2≤current alpha=3: this branch cannot reach MAX's threshold; stop.\n\nTT_BETA: lower bound: Stored 9≥current beta=8: MIN has a lower alternative; stop.\n\nInsufficient depth: Do not substitute a shallow score for deeper search; still try best_move first.\n\nUse bounds as bounds; a shallow best move can still guide deeper search.",
      "sources": [
        "xiangqi_ai.cpp:1156-1170",
        "xiangqi_ai.cpp:1521-1540"
      ],
      "takeaway": "Use bounds as bounds; a shallow best move can still guide deeper search."
    },
    {
      "id": "s20",
      "title": "Fingerprints also detect repeated positions",
      "eyebrow": "A second use for hashing",
      "layout": "cards",
      "lead": "Store keys along the current search path to find whether the position occurred earlier.",
      "cards": [
        {
          "title": "Current identity",
          "text": "current_hash represents piece placement and side to move."
        },
        {
          "title": "Path history",
          "text": "Save the new position's fingerprint after each move."
        },
        {
          "title": "Repetition",
          "text": "A matching earlier key identifies a return to the same state."
        }
      ],
      "steps": [
        "After make, append the new key to the current path.",
        "At each node, look for a matching earlier state.",
        "The key locates repetitions; adjudication also needs the move history."
      ],
      "notes": "Store keys along the current search path to find whether the position occurred earlier.\n\nAfter make, append the new key to the current path.\n\nAt each node, look for a matching earlier state.\n\nThe key locates repetitions; adjudication also needs the move history.\n\nCurrent identity: current_hash represents piece placement and side to move.\n\nPath history: Save the new position's fingerprint after each move.\n\nRepetition: A matching earlier key identifies a return to the same state.\n\nOne fingerprint supports both cache lookup and path repetition detection.",
      "sources": [
        "xiangqi_ai.cpp:302-306",
        "xiangqi_ai.cpp:633-660",
        "xiangqi_ai.cpp:1129-1159"
      ],
      "takeaway": "One fingerprint supports both cache lookup and path repetition detection."
    },
    {
      "id": "s21",
      "title": "Quiet moves capture nothing. Which comes first?",
      "eyebrow": "Move ordering · The basic problem",
      "layout": "tree",
      "lead": "Quiet moves are non-captures, so victim value cannot order them.",
      "tree": {
        "kind": "ordering",
        "before": [
          "A: preparation",
          "B: defense",
          "C: adjustment",
          "D: cutoff"
        ],
        "after": [
          "Search D first",
          "Tighten bounds immediately",
          "Stop A / B / C earlier"
        ],
        "stage": 1
      },
      "cards": [
        {
          "title": "All candidates are legal",
          "text": "Ordering changes recursion order without removing moves."
        },
        {
          "title": "Cutoff move last",
          "text": "Three subtrees are explored before alpha-beta gets a strong bound."
        },
        {
          "title": "Cutoff move first",
          "text": "The same tree establishes sooner that other candidates need no further work."
        }
      ],
      "steps": [
        "This project calls non-captures quiet moves.",
        "Quiet moves have no captured-piece value to compare.",
        "If D is last, we have already paid for A/B/C subtrees.",
        "Moving D earlier preserves Minimax's result and activates alpha-beta sooner."
      ],
      "notes": "Quiet moves are non-captures, so victim value cannot order them.\n\nThis project calls non-captures quiet moves.\n\nQuiet moves have no captured-piece value to compare.\n\nIf D is last, we have already paid for A/B/C subtrees.\n\nMoving D earlier preserves Minimax's result and activates alpha-beta sooner.\n\nAll candidates are legal: Ordering changes recursion order without removing moves.\n\nCutoff move last: Three subtrees are explored before alpha-beta gets a strong bound.\n\nCutoff move first: The same tree establishes sooner that other candidates need no further work.\n\nOrdering tests likely bound-improving moves earlier.",
      "sources": [
        "xiangqi_ai.cpp:1271-1302"
      ],
      "takeaway": "Ordering tests likely bound-improving moves earlier."
    },
    {
      "id": "s21a",
      "title": "Three memory tables: ply, reply, and history",
      "eyebrow": "Quiet-move ordering · Real indices and updates",
      "layout": "compare",
      "lead": "All three update only when a quiet move actually causes an alpha-beta cutoff.",
      "table": {
        "headers": [
          "Heuristic",
          "Lookup key",
          "Stored information"
        ],
        "rows": [
          [
            "killer",
            "killer_moves[ply][0 / 1]",
            "Two recent successful quiet moves at the same search ply"
          ],
          [
            "counter",
            "counter_move[previous source][previous destination]",
            "A quiet move that cut off after that complete previous move"
          ],
          [
            "history",
            "history_table[current source][current destination]",
            "Accumulated cutoff experience for that source/destination pair"
          ]
        ]
      },
      "code": "bonus = depth * depth;\nhistory[successful_quiet] += bonus;\nfor (quiet : earlier_searched_quiets)\n  history[quiet] -= bonus;\nhistory = clamp(history, -(1<<20), +(1<<20));",
      "cards": [
        {
          "title": "Two killer slots",
          "text": "New move enters slot 0; old slot 0 becomes slot 1. No grouping by position or piece type."
        },
        {
          "title": "Counter key",
          "text": "All four previous-move coordinates, not just the destination."
        },
        {
          "title": "History limits",
          "text": "Depth² rewards and penalties, capped at ±2²⁰, without periodic decay."
        }
      ],
      "steps": [
        "Killer stores two moves per ply, shared across positions at that ply.",
        "Counter indexes a reply by the previous move's four coordinates.",
        "History accumulates positive and negative experience for candidate coordinates.",
        "Captures do not update these tables even when they cause cutoffs."
      ],
      "notes": "All three update only when a quiet move actually causes an alpha-beta cutoff.\n\nKiller stores two moves per ply, shared across positions at that ply.\n\nCounter indexes a reply by the previous move's four coordinates.\n\nHistory accumulates positive and negative experience for candidate coordinates.\n\nCaptures do not update these tables even when they cause cutoffs.\n\nTwo killer slots: New move enters slot 0; old slot 0 becomes slot 1. No grouping by position or piece type.\n\nCounter key: All four previous-move coordinates, not just the destination.\n\nHistory limits: Depth² rewards and penalties, capped at ±2²⁰, without periodic decay.\n\nThe tables remember success at this ply, after this reply, and across long-term move history.",
      "sources": [
        "xiangqi_ai.cpp:325-327",
        "xiangqi_ai.cpp:416-425",
        "xiangqi_ai.cpp:1262-1269",
        "xiangqi_ai.cpp:1446-1505",
        "xiangqi_ai.cpp:1746-1760"
      ],
      "takeaway": "The tables remember success at this ply, after this reply, and across long-term move history."
    },
    {
      "id": "s21b",
      "title": "How do five candidates become an ordered queue?",
      "eyebrow": "Move ordering · Actual tiers",
      "layout": "compare",
      "lead": "These numbers are ordering keys, not evaluations or substitutes for search.",
      "table": {
        "headers": [
          "Candidate",
          "Signal",
          "Source ordering score"
        ],
        "rows": [
          [
            "A: cannon takes rook, SEE nonnegative",
            "Good capture",
            "10,000,000 + 1000×10 − 450 = 10,009,550"
          ],
          [
            "B: quiet move",
            "Killer slot 0",
            "9,000,000"
          ],
          [
            "C: quiet move",
            "counter",
            "7,000,000"
          ],
          [
            "D: quiet move",
            "history",
            "12,500"
          ],
          [
            "E: quiet move",
            "history",
            "−3,000"
          ]
        ]
      },
      "code": "if (move == tt_move)      score = 300000000;\nelse if (good_capture)       score = 10000000 + victim*10 - attacker;\nelse if (move == killer1)    score = 9000000;\nelse if (move == killer2)    score = 8000000;\nelse if (move == counter)    score = 7000000;\nelse                         score = history[from][to];",
      "cards": [
        {
          "title": "Example queue",
          "text": "A good capture → B killer → C counter → D history → E history"
        },
        {
          "title": "Multiple signals",
          "text": "An else-if chain uses the first matching tier; killer, counter, and history do not add together."
        },
        {
          "title": "Captures vs experience",
          "text": "Captures take their own branch; killer/counter/history order quiet moves."
        }
      ],
      "steps": [
        "A TT best move receives 300 million and goes first.",
        "Good captures use the 10-million tier, refined by victim and attacker values.",
        "Killer slots use 9/8 million; counter uses 7 million.",
        "Remaining quiet moves use descending history scores."
      ],
      "notes": "These numbers are ordering keys, not evaluations or substitutes for search.\n\nA TT best move receives 300 million and goes first.\n\nGood captures use the 10-million tier, refined by victim and attacker values.\n\nKiller slots use 9/8 million; counter uses 7 million.\n\nRemaining quiet moves use descending history scores.\n\nExample queue: A good capture → B killer → C counter → D history → E history\n\nMultiple signals: An else-if chain uses the first matching tier; killer, counter, and history do not add together.\n\nCaptures vs experience: Captures take their own branch; killer/counter/history order quiet moves.\n\nOrdering keys determine trial order: captures establish bounds, then experience orders quiet moves.",
      "sources": [
        "xiangqi_ai.cpp:91-100",
        "xiangqi_ai.cpp:1271-1302"
      ],
      "takeaway": "Ordering keys determine trial order: captures establish bounds, then experience orders quiet moves."
    },
    {
      "id": "s25",
      "title": "We can reason through replies. Now search deeper",
      "eyebrow": "Transition · Next chapter",
      "layout": "map",
      "lead": "Minimax models opponents; alpha-beta uses bounds; QS stabilizes leaves; TT reuses evidence; ordering and iterative deepening meet deadlines.",
      "cards": [
        {
          "title": "Completed",
          "text": "Search logic, bound-based cutoffs, tactical leaves, caching, ordering, and timely answers"
        },
        {
          "title": "Next question",
          "text": "Even with good ordering, there are too many moves. Which can we reduce or skip?"
        },
        {
          "title": "Risk",
          "text": "The next chapter moves from provable bounds to heuristic choices, with missed-move risk."
        }
      ],
      "steps": [
        "We can model opponents, use bounds, stabilize leaves, reuse memory, and return on time.",
        "Search depth remains limited.",
        "Next: find guide moves, use cheap probes, and prune heuristically."
      ],
      "notes": "Minimax models opponents; alpha-beta uses bounds; QS stabilizes leaves; TT reuses evidence; ordering and iterative deepening meet deadlines.\n\nWe can model opponents, use bounds, stabilize leaves, reuse memory, and return on time.\n\nSearch depth remains limited.\n\nNext: find guide moves, use cheap probes, and prune heuristically.\n\nCompleted: Search logic, bound-based cutoffs, tactical leaves, caching, ordering, and timely answers\n\nNext question: Even with good ordering, there are too many moves. Which can we reduce or skip?\n\nRisk: The next chapter moves from provable bounds to heuristic choices, with missed-move risk.\n\nBuild a reliable search structure before trading heuristic risk for depth.",
      "sources": [
        "xiangqi_ai.cpp:1123",
        "xiangqi_ai.cpp:1030",
        "xiangqi_ai.cpp:1156",
        "xiangqi_ai.cpp:1262",
        "xiangqi_ai.cpp:1545"
      ],
      "takeaway": "Build a reliable search structure before trading heuristic risk for depth."
    }
  ]
});
