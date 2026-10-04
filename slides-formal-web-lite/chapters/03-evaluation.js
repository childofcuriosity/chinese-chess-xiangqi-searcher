window.XQ_CHAPTERS = window.XQ_CHAPTERS || [];
window.XQ_CHAPTERS.push({
  "id": "03",
  "title": "Stage 2: Evaluating positions",
  "slides": [
    {
      "id": "e01",
      "eyebrow": "Stage 2 · Evaluation",
      "title": "We can move. Which move should we choose?",
      "layout": "board",
      "lead": "There may be dozens of legal moves. We need a language for comparing future positions.",
      "boards": [
        {
          "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
          "caption": "Initial position · Red to move",
          "orientation": "red"
        }
      ],
      "steps": [
        "A position where the search stops expanding is a leaf.",
        "At a leaf, how do we decide who is better?",
        "Turn intuition into a comparable number."
      ],
      "cards": [
        {
          "title": "Input",
          "text": "A specific position"
        },
        {
          "title": "Output",
          "text": "A static evaluation score"
        }
      ],
      "notes": "There may be dozens of legal moves. We need a language for comparing future positions.\n\nA position where the search stops expanding is a leaf.\n\nAt a leaf, how do we decide who is better?\n\nTurn intuition into a comparable number.\n\nInput: A specific position\n\nOutput: A static evaluation score\n\nEvaluation gives search leaves a common scale.",
      "sources": [
        "xiangqi_ai.cpp:791"
      ],
      "takeaway": "Evaluation gives search leaves a common scale."
    },
    {
      "id": "e02",
      "eyebrow": "The first measure",
      "title": "Basic intuition: how much material remains?",
      "layout": "table",
      "lead": "Assign each piece type a base value, then sum for Red and Black.",
      "table": {
        "headers": [
          "Piece",
          "King",
          "Rook",
          "Horse",
          "Cannon",
          "Advisor / elephant",
          "Pawn"
        ],
        "rows": [
          [
            "Project base values",
            "10000",
            "1000",
            "450",
            "450",
            "120",
            "100"
          ]
        ]
      },
      "steps": [
        "Red material total − Black material total",
        "Winning a rook is usually worth more than winning a pawn."
      ],
      "code": "score = sum(Red piece values) − sum(Black piece values);",
      "notes": "Assign each piece type a base value, then sum for Red and Black.\n\nRed material total − Black material total\n\nWinning a rook is usually worth more than winning a pawn.\n\nMaterial describes what remains, but not where it stands.",
      "sources": [
        "xiangqi_ai.cpp:91-106"
      ],
      "takeaway": "Material describes what remains, but not where it stands."
    },
    {
      "id": "e03",
      "eyebrow": "A first counterexample",
      "title": "Same pieces, same position quality?",
      "layout": "compare",
      "lead": "Material is identical; the pawn on the right has crossed the river, yet material-only scores are equal.",
      "boards": [
        {
          "fen": "9/9/5k3/9/9/4P4/9/9/9/3K5 w",
          "caption": "Red to move · Central pawn before crossing",
          "orientation": "red",
          "highlights": [
            {
              "square": "e5",
              "kind": "focus"
            }
          ],
          "annotations": [
            {
              "square": "e5",
              "text": "Same pawn"
            }
          ]
        },
        {
          "fen": "9/9/5k3/9/4P4/9/9/9/9/3K5 w",
          "caption": "Red to move · Central pawn after crossing",
          "orientation": "red",
          "highlights": [
            {
              "square": "e4",
              "kind": "focus"
            }
          ],
          "annotations": [
            {
              "square": "e4",
              "text": "New square"
            }
          ]
        }
      ],
      "steps": [
        "Material is unchanged.",
        "After crossing, the pawn also gains sideways movement.",
        "Can evaluation account for placement?"
      ],
      "notes": "Material is identical; the pawn on the right has crossed the river, yet material-only scores are equal.\n\nMaterial is unchanged.\n\nAfter crossing, the pawn also gains sideways movement.\n\nCan evaluation account for placement?\n\nEqual material can deserve different scores: add position.",
      "sources": [
        "xiangqi_ai.cpp:112-123",
        "象棋教学局面核验.md:A2"
      ],
      "takeaway": "Equal material can deserve different scores: add position."
    },
    {
      "id": "e04",
      "eyebrow": "PST",
      "title": "A table of squares for each piece",
      "layout": "heatmap",
      "lead": "PST: piece type × square → a predefined value.",
      "boards": [
        {
          "caption": "Red pawn PST · Red perspective · 90 entries",
          "orientation": "red",
          "heatmap": [
            {
              "square": "a0",
              "value": 9
            },
            {
              "square": "b0",
              "value": 9
            },
            {
              "square": "c0",
              "value": 9
            },
            {
              "square": "d0",
              "value": 11
            },
            {
              "square": "e0",
              "value": 13
            },
            {
              "square": "f0",
              "value": 11
            },
            {
              "square": "g0",
              "value": 9
            },
            {
              "square": "h0",
              "value": 9
            },
            {
              "square": "i0",
              "value": 9
            },
            {
              "square": "a1",
              "value": 39
            },
            {
              "square": "b1",
              "value": 49
            },
            {
              "square": "c1",
              "value": 69
            },
            {
              "square": "d1",
              "value": 84
            },
            {
              "square": "e1",
              "value": 89
            },
            {
              "square": "f1",
              "value": 84
            },
            {
              "square": "g1",
              "value": 69
            },
            {
              "square": "h1",
              "value": 49
            },
            {
              "square": "i1",
              "value": 39
            },
            {
              "square": "a2",
              "value": 39
            },
            {
              "square": "b2",
              "value": 49
            },
            {
              "square": "c2",
              "value": 64
            },
            {
              "square": "d2",
              "value": 74
            },
            {
              "square": "e2",
              "value": 74
            },
            {
              "square": "f2",
              "value": 74
            },
            {
              "square": "g2",
              "value": 64
            },
            {
              "square": "h2",
              "value": 49
            },
            {
              "square": "i2",
              "value": 39
            },
            {
              "square": "a3",
              "value": 39
            },
            {
              "square": "b3",
              "value": 46
            },
            {
              "square": "c3",
              "value": 54
            },
            {
              "square": "d3",
              "value": 59
            },
            {
              "square": "e3",
              "value": 61
            },
            {
              "square": "f3",
              "value": 59
            },
            {
              "square": "g3",
              "value": 54
            },
            {
              "square": "h3",
              "value": 46
            },
            {
              "square": "i3",
              "value": 39
            },
            {
              "square": "a4",
              "value": 29
            },
            {
              "square": "b4",
              "value": 37
            },
            {
              "square": "c4",
              "value": 41
            },
            {
              "square": "d4",
              "value": 54
            },
            {
              "square": "e4",
              "value": 59
            },
            {
              "square": "f4",
              "value": 54
            },
            {
              "square": "g4",
              "value": 41
            },
            {
              "square": "h4",
              "value": 37
            },
            {
              "square": "i4",
              "value": 29
            },
            {
              "square": "a5",
              "value": 7
            },
            {
              "square": "b5",
              "value": 0
            },
            {
              "square": "c5",
              "value": 13
            },
            {
              "square": "d5",
              "value": 0
            },
            {
              "square": "e5",
              "value": 16
            },
            {
              "square": "f5",
              "value": 0
            },
            {
              "square": "g5",
              "value": 13
            },
            {
              "square": "h5",
              "value": 0
            },
            {
              "square": "i5",
              "value": 7
            },
            {
              "square": "a6",
              "value": 7
            },
            {
              "square": "b6",
              "value": 0
            },
            {
              "square": "c6",
              "value": 7
            },
            {
              "square": "d6",
              "value": 0
            },
            {
              "square": "e6",
              "value": 15
            },
            {
              "square": "f6",
              "value": 0
            },
            {
              "square": "g6",
              "value": 7
            },
            {
              "square": "h6",
              "value": 0
            },
            {
              "square": "i6",
              "value": 7
            },
            {
              "square": "a7",
              "value": 0
            },
            {
              "square": "b7",
              "value": 0
            },
            {
              "square": "c7",
              "value": 0
            },
            {
              "square": "d7",
              "value": 0
            },
            {
              "square": "e7",
              "value": 0
            },
            {
              "square": "f7",
              "value": 0
            },
            {
              "square": "g7",
              "value": 0
            },
            {
              "square": "h7",
              "value": 0
            },
            {
              "square": "i7",
              "value": 0
            },
            {
              "square": "a8",
              "value": 0
            },
            {
              "square": "b8",
              "value": 0
            },
            {
              "square": "c8",
              "value": 0
            },
            {
              "square": "d8",
              "value": 0
            },
            {
              "square": "e8",
              "value": 0
            },
            {
              "square": "f8",
              "value": 0
            },
            {
              "square": "g8",
              "value": 0
            },
            {
              "square": "h8",
              "value": 0
            },
            {
              "square": "i8",
              "value": 0
            },
            {
              "square": "a9",
              "value": 0
            },
            {
              "square": "b9",
              "value": 0
            },
            {
              "square": "c9",
              "value": 0
            },
            {
              "square": "d9",
              "value": 0
            },
            {
              "square": "e9",
              "value": 0
            },
            {
              "square": "f9",
              "value": 0
            },
            {
              "square": "g9",
              "value": 0
            },
            {
              "square": "h9",
              "value": 0
            },
            {
              "square": "i9",
              "value": 0
            }
          ],
          "heatMax": 100
        }
      ],
      "steps": [
        "A lookup takes O(1).",
        "Black uses the same table with ranks mirrored.",
        "Zeros on the rear three ranks mark unreachable pawn squares, not worthless legal squares."
      ],
      "notes": "PST: piece type × square → a predefined value.\n\nA lookup takes O(1).\n\nBlack uses the same table with ranks mirrored.\n\nZeros on the rear three ranks mark unreachable pawn squares, not worthless legal squares.\n\nOne PST lookup combines piece type and location.",
      "sources": [
        "xiangqi_ai.cpp:109-123",
        "xiangqi_ai.cpp:434-441"
      ],
      "takeaway": "One PST lookup combines piece type and location."
    },
    {
      "id": "e05",
      "eyebrow": "PST suggests; search checks consequences",
      "title": "What does 16 → 59 → 89 → 13 express?",
      "layout": "compare",
      "lead": "Four diagrams show one pawn's table value at four points on a file.",
      "boards": [
        {
          "fen": "9/9/5k3/9/9/4P4/9/9/9/3K5 w",
          "caption": "Before crossing · 16",
          "orientation": "red",
          "highlights": [
            {
              "square": "e5",
              "kind": "focus"
            }
          ],
          "annotations": [
            {
              "square": "e5",
              "text": "16"
            }
          ]
        },
        {
          "fen": "9/9/5k3/9/4P4/9/9/9/9/3K5 w",
          "caption": "Just crossed · 59",
          "orientation": "red",
          "highlights": [
            {
              "square": "e4",
              "kind": "focus"
            }
          ],
          "annotations": [
            {
              "square": "e4",
              "text": "59"
            }
          ]
        },
        {
          "fen": "9/4P4/5k3/9/9/9/9/9/9/3K5 w",
          "caption": "Penultimate rank · 89",
          "orientation": "red",
          "highlights": [
            {
              "square": "e1",
              "kind": "focus"
            }
          ],
          "annotations": [
            {
              "square": "e1",
              "text": "89"
            }
          ]
        },
        {
          "fen": "4P4/9/5k3/9/9/9/9/9/9/3K5 w",
          "caption": "Back rank · 13",
          "orientation": "red",
          "highlights": [
            {
              "square": "e0",
              "kind": "focus"
            }
          ],
          "annotations": [
            {
              "square": "e0",
              "text": "13"
            }
          ]
        }
      ],
      "steps": [
        "The table favors advanced pawns on the penultimate rank.",
        "The back-rank value 13 is a static preference; search determines tactical value."
      ],
      "notes": "Four diagrams show one pawn's table value at four points on a file.\n\nThe table favors advanced pawns on the penultimate rank.\n\nThe back-rank value 13 is a static preference; search determines tactical value.\n\nPST encodes heuristics; the position and search determine the outcome.",
      "sources": [
        "xiangqi_ai.cpp:112-123",
        "象棋教学局面核验.md:对当前预览稿的棋理教学审查"
      ],
      "takeaway": "PST encodes heuristics; the position and search determine the outcome."
    },
    {
      "id": "s06",
      "title": "Wins and losses are not ordinary scores",
      "eyebrow": "Evaluation limits · Terminal scores",
      "layout": "cards",
      "lead": "Material and position compare ongoing games; decisive outcomes use scores near ±30000.",
      "cards": [
        {
          "title": "Ongoing position",
          "text": "Material and square values measure relative positional quality."
        },
        {
          "title": "Red wins",
          "text": "Black king absent, or Black has no legal move: return near +30000."
        },
        {
          "title": "Black wins",
          "text": "Red king absent, or Red has no legal move: return near −30000."
        },
        {
          "title": "Why separate them?",
          "text": "A decisive outcome must outweigh ordinary material or positional gains."
        }
      ],
      "steps": [
        "SCORE_INF is 30000 in this project.",
        "A missing king or no legal move establishes a decisive result.",
        "Terminal scores greatly exceed ordinary evaluation magnitudes."
      ],
      "notes": "Material and position compare ongoing games; decisive outcomes use scores near ±30000.\n\nSCORE_INF is 30000 in this project.\n\nA missing king or no legal move establishes a decisive result.\n\nTerminal scores greatly exceed ordinary evaluation magnitudes.\n\nOngoing position: Material and square values measure relative positional quality.\n\nRed wins: Black king absent, or Black has no legal move: return near +30000.\n\nBlack wins: Red king absent, or Red has no legal move: return near −30000.\n\nWhy separate them?: A decisive outcome must outweigh ordinary material or positional gains.\n\nStatic evaluation compares ongoing positions; terminal scores encode decisive outcomes.",
      "sources": [
        "xiangqi_ai.cpp:31-32",
        "xiangqi_ai.cpp:1172-1173",
        "xiangqi_ai.cpp:1516-1519"
      ],
      "takeaway": "Static evaluation compares ongoing positions; terminal scores encode decisive outcomes."
    },
    {
      "id": "e06",
      "eyebrow": "Evaluation × Search",
      "title": "Why advance the pawn for a static loss of 60?",
      "layout": "compare",
      "lead": "Capturing the horse looks better immediately; exploring replies reveals a winning alternative.",
      "boards": [
        {
          "fen": "3n1k3/5nP2/9/9/9/9/9/9/9/4K4 w",
          "caption": "Before · Red to move · Two candidates",
          "orientation": "red",
          "highlights": [
            {
              "square": "g1",
              "kind": "from"
            },
            {
              "square": "f1",
              "kind": "danger"
            },
            {
              "square": "g0",
              "kind": "to"
            }
          ],
          "arrows": [
            {
              "from": "g1",
              "to": "f1",
              "kind": "secondary"
            },
            {
              "from": "g1",
              "to": "g0",
              "kind": "primary"
            }
          ],
          "annotations": []
        },
        {
          "fen": "3n1k3/5P3/9/9/9/9/9/9/9/4K4 b",
          "caption": "Pawn captures horse sideways; Black king can recapture on (1,5)",
          "orientation": "red",
          "highlights": [
            {
              "square": "f0",
              "kind": "from"
            },
            {
              "square": "f1",
              "kind": "danger"
            }
          ],
          "arrows": [
            {
              "from": "f0",
              "to": "f1",
              "kind": "secondary"
            }
          ]
        },
        {
          "fen": "3n1kP2/5n3/9/9/9/9/9/9/9/4K4 b",
          "caption": "Pawn advances; Black cannot escape check: mate in one",
          "orientation": "red",
          "highlights": [
            {
              "square": "g0",
              "kind": "focus"
            },
            {
              "square": "f0",
              "kind": "danger"
            }
          ],
          "arrows": [
            {
              "from": "g0",
              "to": "f0",
              "kind": "primary"
            }
          ]
        }
      ],
      "cards": [
        {
          "title": "Immediate capture gain",
          "text": "Black horse total 102; pawn rises from 69 to 84: static gain +117."
        },
        {
          "title": "Static advance cost",
          "text": "Pawn PST falls from 69 to 9: −60."
        },
        {
          "title": "After searching",
          "text": "Advancing delivers mate, returning a score near +30000."
        }
      ],
      "steps": [
        "Material gain usually exceeds a small positional improvement, making the capture attractive.",
        "Black's king recaptures the pawn; search removes it and continues the exchange line.",
        "The advance loses 60 statically but leaves Black no escape from check."
      ],
      "notes": "Capturing the horse looks better immediately; exploring replies reveals a winning alternative.\n\nMaterial gain usually exceeds a small positional improvement, making the capture attractive.\n\nBlack's king recaptures the pawn; search removes it and continues the exchange line.\n\nThe advance loses 60 statically but leaves Black no escape from check.\n\nImmediate capture gain: Black horse total 102; pawn rises from 69 to 84: static gain +117.\n\nStatic advance cost: Pawn PST falls from 69 to 9: −60.\n\nAfter searching: Advancing delivers mate, returning a score near +30000.\n\nSearch follows exchanges; their net gain is still below the alternative's decisive win.",
      "sources": [
        "xiangqi_ai.cpp:112-123",
        "xiangqi_ai.cpp:182-195",
        "xiangqi_ai.cpp:434-441",
        "xiangqi_ai.cpp:1516-1518"
      ],
      "takeaway": "Search follows exchanges; their net gain is still below the alternative's decisive win."
    },
    {
      "id": "e08",
      "eyebrow": "Avoid scanning all 90 squares",
      "title": "A quiet advance changes only two values",
      "layout": "compare",
      "lead": "The same legal central-pawn advance, with an empty target.",
      "boards": [
        {
          "fen": "9/9/5k3/9/9/4P4/9/9/9/3K5 w",
          "caption": "Before advance · Pawn value 16",
          "orientation": "red",
          "highlights": [
            {
              "square": "e5",
              "kind": "from"
            }
          ],
          "arrows": [
            {
              "from": "e5",
              "to": "e4",
              "kind": "primary"
            }
          ]
        },
        {
          "fen": "9/9/5k3/9/4P4/9/9/9/9/3K5 b",
          "caption": "After advance · Pawn value 59",
          "orientation": "red",
          "highlights": [
            {
              "square": "e4",
              "kind": "to"
            }
          ]
        }
      ],
      "code": "Δscore = −16 + 59 = +43",
      "steps": [
        "Δscore = −16 + 59 = +43",
        "Subtract the old square value and add the new one.",
        "Undo applies the exact inverse."
      ],
      "notes": "The same legal central-pawn advance, with an empty target.\n\nΔscore = −16 + 59 = +43\n\nSubtract the old square value and add the new one.\n\nUndo applies the exact inverse.\n\nMaintain evaluation with moves instead of rescanning each search node.",
      "sources": [
        "xiangqi_ai.cpp:485-505",
        "xiangqi_ai.cpp:552-568",
        "象棋教学局面核验.md:A2"
      ],
      "takeaway": "Maintain evaluation with moves instead of rescanning each search node."
    },
    {
      "id": "e09",
      "eyebrow": "Incremental scoring",
      "title": "If the target is occupied, remove its value too",
      "layout": "compare",
      "lead": "The same pawn advance, now capturing a black pawn.",
      "boards": [
        {
          "fen": "9/9/5k3/9/4p4/4P4/9/9/9/3K5 w",
          "caption": "Before · Black pawn ahead",
          "orientation": "red",
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
              "to": "e4",
              "kind": "capture"
            }
          ]
        },
        {
          "fen": "9/9/5k3/9/4P4/9/9/9/9/3K5 b",
          "caption": "After · Black pawn removed",
          "orientation": "red",
          "highlights": [
            {
              "square": "e4",
              "kind": "to"
            }
          ],
          "annotations": [
            {
              "square": "e4",
              "text": "59"
            }
          ]
        }
      ],
      "code": "Δscore = −16 − (−16) + 59 = +59",
      "steps": [
        "Δscore = −16 − (−16) + 59 = +59",
        "Remove the old red-pawn value: −16.",
        "Remove Black's contribution: −(−16); add the new red-pawn value: +59."
      ],
      "notes": "The same pawn advance, now capturing a black pawn.\n\nΔscore = −16 − (−16) + 59 = +59\n\nRemove the old red-pawn value: −16.\n\nRemove Black's contribution: −(−16); add the new red-pawn value: +59.\n\nMoves, captures, and undo update only affected pieces.",
      "sources": [
        "xiangqi_ai.cpp:485-505",
        "象棋教学局面核验.md:A1"
      ],
      "takeaway": "Moves, captures, and undo update only affected pieces."
    },
    {
      "id": "e10",
      "eyebrow": "A second counterexample",
      "title": "Independent square values miss relationships",
      "layout": "board",
      "lead": "Adding separate piece scores loses interactions between pieces.",
      "cards": [
        {
          "title": "Defensive structure",
          "text": "Mutual protection by advisors and elephants is a relationship, not one square value."
        },
        {
          "title": "Open-file cannon",
          "text": "Its value depends on the line and occupancy between cannon and enemy king."
        },
        {
          "title": "Pins / control",
          "text": "Moving one piece can change another piece's legal space."
        }
      ],
      "boards": [
        {
          "fen": "4k4/9/9/9/4C4/9/9/9/9/3K5 w",
          "caption": "Open-file cannon · No screen, so no current check",
          "orientation": "red",
          "highlights": [
            {
              "square": "e0",
              "kind": "focus"
            },
            {
              "square": "e4",
              "kind": "focus"
            }
          ],
          "annotations": [
            {
              "square": "e2",
              "text": "No screen"
            }
          ]
        }
      ],
      "steps": [
        "PST asks only: what piece, and where?",
        "Relational features ask: with whom, behind which blocker, controlling what together?"
      ],
      "notes": "Adding separate piece scores loses interactions between pieces.\n\nPST asks only: what piece, and where?\n\nRelational features ask: with whom, behind which blocker, controlling what together?\n\nDefensive structure: Mutual protection by advisors and elephants is a relationship, not one square value.\n\nOpen-file cannon: Its value depends on the line and occupancy between cannon and enemy king.\n\nPins / control: Moving one piece can change another piece's legal space.\n\nSingle-piece features are cheap; richer relationships require more computation.",
      "sources": [
        "如何写一个业余象棋引擎.pdf:P12-P13",
        "xiangqi_ai.cpp:791"
      ],
      "takeaway": "Single-piece features are cheap; richer relationships require more computation."
    },
    {
      "id": "e17",
      "eyebrow": "Another evaluation path · 1/5",
      "title": "Model relationships while updating few features",
      "layout": "compare",
      "lead": "NNUE extends the incremental PST idea from one number to a vector of intermediate features.",
      "boards": [
        {
          "fen": "9/9/5k3/9/9/4P4/9/9/9/3K5 w",
          "caption": "Before · Pawn has not crossed",
          "orientation": "red",
          "highlights": [
            {
              "square": "e5",
              "kind": "from"
            }
          ],
          "arrows": [
            {
              "from": "e5",
              "to": "e4",
              "kind": "primary"
            }
          ]
        },
        {
          "fen": "9/9/5k3/9/4P4/9/9/9/9/3K5 b",
          "caption": "After advance · Pawn has crossed",
          "orientation": "red",
          "highlights": [
            {
              "square": "e4",
              "kind": "to"
            }
          ]
        }
      ],
      "cards": [
        {
          "title": "PST",
          "text": "P[pawn, square] is a scalar: one number."
        },
        {
          "title": "NNUE",
          "text": "W[pawn, square] is a first-layer weight column: a vector."
        }
      ],
      "code": "PST:  S' = S − P[pawn, old] + P[pawn, new]\nNNUE: A' = A − W[pawn, old] + W[pawn, new]",
      "steps": [
        "Only a few piece-on-square features are active.",
        "Both PST and NNUE subtract the old feature and add the new one."
      ],
      "notes": "NNUE extends the incremental PST idea from one number to a vector of intermediate features.\n\nOnly a few piece-on-square features are active.\n\nBoth PST and NNUE subtract the old feature and add the new one.\n\nPST: P[pawn, square] is a scalar: one number.\n\nNNUE: W[pawn, square] is a first-layer weight column: a vector.\n\nPST updates a scalar; NNUE updates a vector. Both touch only changed features.",
      "sources": [
        "https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html",
        "pikafish-pst/src/evaluate.cpp:143-176",
        "pikafish-pst/src/nnue/nnue_accumulator.h:19-21",
        "xiangqi_ai.cpp:791"
      ],
      "takeaway": "PST updates a scalar; NNUE updates a vector. Both touch only changed features."
    },
    {
      "id": "e17b",
      "eyebrow": "Another evaluation path · 2/5",
      "title": "Cache the first-layer sum in an accumulator",
      "layout": "code",
      "lead": "A stores the sum of contributions from all active board features.",
      "code": "Accumulator      A = [10, 20]\nOld contribution Wold = [2, 3]\nNew contribution Wnew = [5, 4]\n\nA' = A − Wold + Wnew\n   = [10,20] − [2,3] + [5,4]\n   = [13,21]",
      "codeNote": "Two-dimensional teaching example, not actual network weights.",
      "cards": [
        {
          "title": "Weight vector W",
          "text": "The learned contribution of one piece-square feature."
        },
        {
          "title": "Accumulator A",
          "text": "Sum all active feature columns and retain the result."
        }
      ],
      "steps": [
        "The pawn leaves its old square: subtract that column.",
        "It appears on the new square: add that column.",
        "Other pieces' contributions remain cached in A."
      ],
      "notes": "A stores the sum of contributions from all active board features.\n\nThe pawn leaves its old square: subtract that column.\n\nIt appears on the new square: add that column.\n\nOther pieces' contributions remain cached in A.\n\nWeight vector W: The learned contribution of one piece-square feature.\n\nAccumulator A: Sum all active feature columns and retain the result.\n\nThe accumulator replaces full recomputation with subtract-old, add-new.",
      "sources": [
        "https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html#updating-the-accumulator"
      ],
      "takeaway": "The accumulator replaces full recomputation with subtract-old, add-new."
    },
    {
      "id": "e17c",
      "eyebrow": "Another evaluation path · 3/5",
      "title": "Captures also subtract the captured vector",
      "layout": "compare",
      "lead": "The pawn advances again, this time onto a black pawn.",
      "boards": [
        {
          "fen": "9/9/5k3/9/4p4/4P4/9/9/9/3K5 w",
          "caption": "Before · Black pawn ahead",
          "orientation": "red",
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
              "to": "e4",
              "kind": "capture"
            }
          ]
        },
        {
          "fen": "9/9/5k3/9/4P4/9/9/9/9/3K5 b",
          "caption": "After · Black pawn removed",
          "orientation": "red",
          "highlights": [
            {
              "square": "e4",
              "kind": "to"
            }
          ]
        }
      ],
      "code": "A' = A\n   − W[red pawn, old square]\n   − W[black pawn, captured square]\n   + W[red pawn, new square]",
      "steps": [
        "Moving piece: subtract its old feature and add its new feature.",
        "Captured piece: subtract its feature vector too.",
        "An ordinary non-king move usually changes only these few inputs."
      ],
      "notes": "The pawn advances again, this time onto a black pawn.\n\nMoving piece: subtract its old feature and add its new feature.\n\nCaptured piece: subtract its feature vector too.\n\nAn ordinary non-king move usually changes only these few inputs.\n\nMoves and captures incrementally update only changed first-layer columns.",
      "sources": [
        "https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html#updating-the-accumulator",
        "象棋教学局面核验.md:A1"
      ],
      "takeaway": "Moves and captures incrementally update only changed first-layer columns."
    },
    {
      "id": "e17d",
      "eyebrow": "Another evaluation path · 4/5",
      "title": "The accumulator still needs an output network",
      "layout": "figure",
      "lead": "Incremental updates save first-layer summation; this project minimizes the remaining network to preserve search depth.",
      "figure": {
        "src": "assets/nnue/stockfish-a-features-network.svg",
        "alt": "Stockfish NNUE teaching diagram: sparse board features feed a wide first layer, smaller hidden layers, and a position score.",
        "caption": "Official chess NNUE diagram; this project reuses the incremental wide-layer idea with a smaller direct output head.",
        "credit": "Stockfish nnue-pytorch documentation · GPLv3",
        "legend": [
          {
            "color": "#10c940",
            "text": "Dark green: piece-square features"
          },
          {
            "color": "#b8efd0",
            "text": "Light green: incremental first layer A"
          },
          {
            "color": "#fff100",
            "text": "Yellow: subsequent network"
          },
          {
            "color": "#f20d17",
            "text": "Red: final score"
          }
        ]
      },
      "steps": [
        "First layer: 11,340 sparse features share weights for two H16 accumulators.",
        "Activation: CReLU clips each component to its valid range.",
        "Direct head: concatenate mover/opponent views; select a middlegame/endgame head to predict the PST residual."
      ],
      "notes": "Incremental updates save first-layer summation; this project minimizes the remaining network to preserve search depth.\n\nFirst layer: 11,340 sparse features share weights for two H16 accumulators.\n\nActivation: CReLU clips each component to its valid range.\n\nDirect head: concatenate mover/opponent views; select a middlegame/endgame head to predict the PST residual.\n\nAn H16 direct head learns interactions while keeping per-node inference cheap.",
      "sources": [
        "https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html",
        "trainnnue/nnue_engine.cpp",
        "trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue.json"
      ],
      "takeaway": "An H16 direct head learns interactions while keeping per-node inference cheap."
    },
    {
      "id": "e17e",
      "eyebrow": "Another evaluation path · 5/5",
      "title": "Addition alone is still just a larger table",
      "layout": "table",
      "lead": "Nonlinearity lets two features together trigger an effect neither creates alone.",
      "table": {
        "headers": [
          "Feature x",
          "Feature y",
          "x + y",
          "h = max(0, x + y − 1)"
        ],
        "rows": [
          [
            "0",
            "0",
            "0",
            "0"
          ],
          [
            "1",
            "0",
            "1",
            "0"
          ],
          [
            "0",
            "1",
            "1",
            "0"
          ],
          [
            "1",
            "1",
            "2",
            "1"
          ]
        ]
      },
      "code": "h = max(0, x + y − 1)\n\nh activates only when both x and y are present.",
      "steps": [
        "Linear sums give each piece-square feature a fixed contribution and collapse back into a PST.",
        "Nonlinear activation makes a feature's effect depend on other active features."
      ],
      "notes": "Nonlinearity lets two features together trigger an effect neither creates alone.\n\nLinear sums give each piece-square feature a fixed contribution and collapse back into a PST.\n\nNonlinear activation makes a feature's effect depend on other active features.\n\nIncremental sums preserve speed; nonlinearity goes beyond fixed square bonuses.",
      "sources": [
        "https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html"
      ],
      "takeaway": "Incremental sums preserve speed; nonlinearity goes beyond fixed square bonuses."
    },
    {
      "id": "e12",
      "eyebrow": "Where does intuition come from?",
      "title": "Can data learn the table values?",
      "layout": "cards",
      "lead": "Represent each historical position as x and its eventual result as y.",
      "cards": [
        {
          "title": "Sample x",
          "text": "The board and required side-to-move information"
        },
        {
          "title": "Label y",
          "text": "Red win = 1; draw = 0.5; Red loss = 0"
        },
        {
          "title": "Parameters θ",
          "text": "Material values, PST entries, or weights of a richer model"
        }
      ],
      "steps": [
        "The model assigns the position a score sθ(x).",
        "Map it to Red's expected score in [0,1].",
        "Train predictions toward historical labels."
      ],
      "notes": "Represent each historical position as x and its eventual result as y.\n\nThe model assigns the position a score sθ(x).\n\nMap it to Red's expected score in [0,1].\n\nTrain predictions toward historical labels.\n\nSample x: The board and required side-to-move information\n\nLabel y: Red win = 1; draw = 0.5; Red loss = 0\n\nParameters θ: Material values, PST entries, or weights of a richer model\n\nTraining fits parameters to positions with outcomes.",
      "sources": [
        "如何写一个业余象棋引擎.pdf:P15"
      ],
      "takeaway": "Training fits parameters to positions with outcomes."
    },
    {
      "id": "e13",
      "eyebrow": "From evaluation to expected score",
      "title": "Sigmoid maps any score to 0–1",
      "layout": "code",
      "lead": "Evaluations may be hundreds or thousands; result labels are 0, 0.5, or 1.",
      "code": "predicted_score(x) = sigmoid(s(x) / K)\n\nsigmoid(z) = 1 / (1 + exp(−z))",
      "cards": [
        {
          "title": "Very negative",
          "text": "Prediction approaches 0"
        },
        {
          "title": "Near zero",
          "text": "Prediction is about 0.5"
        },
        {
          "title": "Very positive",
          "text": "Prediction approaches 1"
        }
      ],
      "steps": [
        "K controls how much evaluation change produces a substantial prediction change.",
        "Estimate K on separate calibration data, then freeze it during network training.",
        "The output is Red's predicted score."
      ],
      "notes": "Evaluations may be hundreds or thousands; result labels are 0, 0.5, or 1.\n\nK controls how much evaluation change produces a substantial prediction change.\n\nEstimate K on separate calibration data, then freeze it during network training.\n\nThe output is Red's predicted score.\n\nVery negative: Prediction approaches 0\n\nNear zero: Prediction is about 0.5\n\nVery positive: Prediction approaches 1\n\nSigmoid aligns evaluation and outcome scales; independently calibrate and freeze K.",
      "sources": [
        "如何写一个业余象棋引擎.pdf:P15",
        "trainnnue/train.py",
        "trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue.json"
      ],
      "takeaway": "Sigmoid aligns evaluation and outcome scales; independently calibrate and freeze K."
    },
    {
      "id": "e14",
      "eyebrow": "Reducing error",
      "title": "MSE penalizes prediction error",
      "layout": "code",
      "lead": "Compute mean squared error over a batch and update parameters along its gradient.",
      "code": "loss = mean((predicted_score(x) − y)²)\n\nExample: prediction 0.8, Red loses (y=0)\nError = (0.8 − 0)² = 0.64\n\nBatch → mean loss → gradient → update θ",
      "steps": [
        "Square each prediction-minus-result error, then average the batch.",
        "Predicting 0.8 for an actual Red loss contributes 0.64.",
        "The entire batch's gradient determines the update direction."
      ],
      "notes": "Compute mean squared error over a batch and update parameters along its gradient.\n\nSquare each prediction-minus-result error, then average the batch.\n\nPredicting 0.8 for an actual Red loss contributes 0.64.\n\nThe entire batch's gradient determines the update direction.\n\nMSE measures prediction error; batch gradients determine parameter updates.",
      "sources": [
        "如何写一个业余象棋引擎.pdf:P15"
      ],
      "takeaway": "MSE measures prediction error; batch gradients determine parameter updates."
    },
    {
      "id": "e14a",
      "eyebrow": "Completed experiment · Search distillation",
      "title": "Teach a model to recognize what search discovers",
      "layout": "code",
      "lead": "The project connects PST teacher search, million-position datasets, NNUE learning, and quantized deployment.",
      "code": "Position x\n  ↓ PST teacher search D3 / D4, selective pruning disabled\nSearch score from the moving side's view\n  ↓ Learn teacher − PST residual\nQuantized value model vθ(x) + original PST",
      "cards": [
        {
          "title": "Teacher",
          "text": "Keep alpha-beta and quiescence; disable selective pruning that could bias labels."
        },
        {
          "title": "Data",
          "text": "One million unique positions each for D3 and D4; 500k per side; split by whole game."
        },
        {
          "title": "Student",
          "text": "Learn the teacher's correction to PST; quantized CPU inference remains inside search."
        }
      ],
      "steps": [
        "Depth is a hyperparameter: D3 is cheaper and easier to fit; D4 is stronger but more expensive.",
        "Deduplicate globally; resolve conflicting labels explicitly or discard the group.",
        "Add a centipawn residual loss to probability error to avoid near-zero corrections.",
        "Quantize to integer weights and test in the same searcher as PST under equal time."
      ],
      "notes": "The project connects PST teacher search, million-position datasets, NNUE learning, and quantized deployment.\n\nDepth is a hyperparameter: D3 is cheaper and easier to fit; D4 is stronger but more expensive.\n\nDeduplicate globally; resolve conflicting labels explicitly or discard the group.\n\nAdd a centipawn residual loss to probability error to avoid near-zero corrections.\n\nQuantize to integer weights and test in the same searcher as PST under equal time.\n\nTeacher: Keep alpha-beta and quiescence; disable selective pruning that could bias labels.\n\nData: One million unique positions each for D3 and D4; 500k per side; split by whole game.\n\nStudent: Learn the teacher's correction to PST; quantized CPU inference remains inside search.\n\nSearch distillation yields a value model cheap enough for live CPU search.",
      "sources": [
        "trainnnue/teacher.cpp",
        "trainnnue/generate_data.cpp",
        "trainnnue/build_balanced_dataset.py",
        "trainnnue/train.py"
      ],
      "takeaway": "Search distillation yields a value model cheap enough for live CPU search."
    },
    {
      "id": "e14b",
      "eyebrow": "Completed experiment · What worked?",
      "title": "Bigger networks and deeper teachers can cost strength",
      "layout": "table",
      "lead": "Offline error screens candidates; quantized equal-CPU-time matches make the final decision.",
      "table": {
        "headers": [
          "Experiment",
          "Observation",
          "Decision"
        ],
        "rows": [
          [
            "Old 150k one-sided D3 + H8",
            "Little data, recording only one side to move",
            "Expand to one million, balanced by side"
          ],
          [
            "Million-position D3: H8 / H16",
            "Easier to fit, weaker in matches than the best D4 model",
            "Use for broad pretraining"
          ],
          [
            "Million-position D4: random / D3 initialization",
            "H16 with D3 initialization has the best validation correlation and match performance",
            "Select as final candidate"
          ],
          [
            "Old D5-H8",
            "Deeper but more expensive and harder for a small network; Swiss score 48.13%",
            "Do not default to the deepest teacher"
          ],
          [
            "Small hidden layer",
            "Adds cost to every leaf evaluation",
            "Choose a direct head this round"
          ]
        ]
      },
      "steps": [
        "Effective: more balanced data, D3-to-D4 initialization, H16 direct head, residual learning.",
        "Not selected: small one-sided data, depth alone, extra hidden layers.",
        "H16's offline gain is modest; direct matches show it covers the speed cost."
      ],
      "notes": "Offline error screens candidates; quantized equal-CPU-time matches make the final decision.\n\nEffective: more balanced data, D3-to-D4 initialization, H16 direct head, residual learning.\n\nNot selected: small one-sided data, depth alone, extra hidden layers.\n\nH16's offline gain is modest; direct matches show it covers the speed cost.\n\nBalanced data, moderate teachers, curriculum initialization, and a light head worked best.",
      "sources": [
        "trainnnue/model_comparison.json",
        "trainnnue/swiss_8models_5rounds.json",
        "trainnnue/d4_balanced1m_h16_fromd3_full100_gpu.nnue.json"
      ],
      "takeaway": "Balanced data, moderate teachers, curriculum initialization, and a light head worked best."
    },
    {
      "id": "e14c",
      "eyebrow": "Completed experiment · Controlled matches",
      "title": "First deployed NNUE scores 59.77% against PST",
      "layout": "cards",
      "lead": "Same search, same CPU time, 192 color-swapped held-out openings; evaluation is the core variable.",
      "cards": [
        {
          "title": "172 wins / 115 draws / 97 losses",
          "text": "Win=1, draw=0.5: NNUE scores 229.5 / 384 points."
        },
        {
          "title": "59.77% score rate",
          "text": "9.77 percentage points above 50%; 95% CI 56.38%–63.15%."
        },
        {
          "title": "H16 vs H8：54.17%",
          "text": "149 wins, 118 draws, 117 losses; the wider model compensates for its small speed cost."
        },
        {
          "title": "363 KB integer model",
          "text": "Mean completed depth 9.24 vs PST 9.70: stronger evaluation costs about 0.46 ply."
        }
      ],
      "steps": [
        "192 openings, each played with both colors, produce 384 games.",
        "Bootstrap opening pairs to retain the correlation between swapped games.",
        "H16 scores 54.17% against H8 with only 0.06 ply difference in mean depth."
      ],
      "notes": "Same search, same CPU time, 192 color-swapped held-out openings; evaluation is the core variable.\n\n192 openings, each played with both colors, produce 384 games.\n\nBootstrap opening pairs to retain the correlation between swapped games.\n\nH16 scores 54.17% against H8 with only 0.06 ply difference in mean depth.\n\n172 wins / 115 draws / 97 losses: Win=1, draw=0.5: NNUE scores 229.5 / 384 points.\n\n59.77% score rate: 9.77 percentage points above 50%; 95% CI 56.38%–63.15%.\n\nH16 vs H8：54.17%: 149 wins, 118 draws, 117 losses; the wider model compensates for its small speed cost.\n\n363 KB integer model: Mean completed depth 9.24 vs PST 9.70: stronger evaluation costs about 0.46 ply.\n\nAfter quantization, first-generation NNUE lifts the equal-time score against PST to 59.77%.",
      "sources": [
        "trainnnue/direct_match_summary.json",
        "trainnnue/RESULTS.generated.md",
        "trainnnue/artifacts.json"
      ],
      "takeaway": "After quantization, first-generation NNUE lifts the equal-time score against PST to 59.77%."
    },
    {
      "id": "e14d",
      "eyebrow": "Completed experiment · Teacher iteration 1",
      "title": "Search D3 with NNUE, then teach the results back",
      "layout": "cards",
      "lead": "A deeper PST teacher is costly; one best-NNUE + D3 iteration generates a new million-position dataset more cheaply.",
      "cards": [
        {
          "title": "Configurable teacher",
          "text": "One generator selects PST or a supplied NNUE; PST remains the compatible default."
        },
        {
          "title": "Balanced million",
          "text": "One million unique positions, 500k per side; only 12 conflict groups discarded."
        },
        {
          "title": "Vs previous model: 60.94%",
          "text": "174 wins, 120 draws, 90 losses; 95% CI 57.16%–64.71%."
        },
        {
          "title": "Vs PST: 63.28%",
          "text": "188 wins, 110 draws, 86 losses; up 3.52 points from 59.77%."
        }
      ],
      "steps": [
        "The quantized D4-H16 evaluates leaves in a three-ply teacher search.",
        "Initialize from the current model, independently calibrate K; best validation at epoch 4.",
        "The student scores 60.94% against its predecessor and 63.28% against PST."
      ],
      "notes": "A deeper PST teacher is costly; one best-NNUE + D3 iteration generates a new million-position dataset more cheaply.\n\nThe quantized D4-H16 evaluates leaves in a three-ply teacher search.\n\nInitialize from the current model, independently calibrate K; best validation at epoch 4.\n\nThe student scores 60.94% against its predecessor and 63.28% against PST.\n\nConfigurable teacher: One generator selects PST or a supplied NNUE; PST remains the compatible default.\n\nBalanced million: One million unique positions, 500k per side; only 12 conflict groups discarded.\n\nVs previous model: 60.94%: 174 wins, 120 draws, 90 losses; 95% CI 57.16%–64.71%.\n\nVs PST: 63.28%: 188 wins, 110 draws, 86 losses; up 3.52 points from 59.77%.\n\nThe first NNUE+D3 iteration beats its predecessor and raises the PST score to 63.28%.",
      "sources": [
        "trainnnue/iter1_experiment.json",
        "trainnnue/generate_data.cpp",
        "trainnnue/iter1_nnued3_h16_fromd4_gpu.nnue.json"
      ],
      "takeaway": "The first NNUE+D3 iteration beats its predecessor and raises the PST score to 63.28%."
    },
    {
      "id": "e14e",
      "eyebrow": "Completed experiment · Teacher iteration 2",
      "title": "Repeat the cycle: 70.18% against PST",
      "layout": "cards",
      "lead": "Iter1 supplies both teacher and initialization; generate a fresh million positions with unchanged architecture and match conditions.",
      "cards": [
        {
          "title": "A new million",
          "text": "Sample exactly one million from 1,057,865 unique valid positions; 500k per side; 15 conflict groups discarded."
        },
        {
          "title": "Independent K=54.708",
          "text": "Calibrate on this iteration's data; best epoch 5, early stop at 25, restore best checkpoint."
        },
        {
          "title": "Vs Iter1: 55.08%",
          "text": "143 wins, 137 draws, 104 losses; 95% CI 51.43%–58.72%, entirely above 50%."
        },
        {
          "title": "Vs PST: 70.18%",
          "text": "218 wins, 103 draws, 63 losses; 95% CI 66.80%–73.44%, up 6.90 points."
        }
      ],
      "steps": [
        "Iter1 evaluates leaves while D3 search generates new labels.",
        "Iter2 starts from Iter1 parameters; best validation at epoch 5.",
        "Iter2 scores 55.08% against Iter1 and 70.18% against PST."
      ],
      "notes": "Iter1 supplies both teacher and initialization; generate a fresh million positions with unchanged architecture and match conditions.\n\nIter1 evaluates leaves while D3 search generates new labels.\n\nIter2 starts from Iter1 parameters; best validation at epoch 5.\n\nIter2 scores 55.08% against Iter1 and 70.18% against PST.\n\nA new million: Sample exactly one million from 1,057,865 unique valid positions; 500k per side; 15 conflict groups discarded.\n\nIndependent K=54.708: Calibrate on this iteration's data; best epoch 5, early stop at 25, restore best checkpoint.\n\nVs Iter1: 55.08%: 143 wins, 137 draws, 104 losses; 95% CI 51.43%–58.72%, entirely above 50%.\n\nVs PST: 70.18%: 218 wins, 103 draws, 63 losses; 95% CI 66.80%–73.44%, up 6.90 points.\n\nThe second iteration beats Iter1 and reaches 70.18% against PST under the same conditions.",
      "sources": [
        "trainnnue/iter2_experiment.json",
        "trainnnue/iter2_nnued3_h16_fromiter1_gpu.nnue.json",
        "trainnnue/RESULTS.generated.md"
      ],
      "takeaway": "The second iteration beats Iter1 and reaches 70.18% against PST under the same conditions."
    },
    {
      "id": "e14f",
      "eyebrow": "Teacher iteration · Common benchmark",
      "title": "Four generations reach 70.18% against PST",
      "layout": "figure",
      "lead": "With architecture, held-out openings, and time controls fixed, generation 3 has the highest observed score.",
      "figure": {
        "src": "assets/nnue/iteration-vs-pst.svg",
        "alt": "PST and four NNUE generations score 50%, 59.77%, 63.28%, 70.18%, and 70.05% against PST.",
        "caption": "192 color-swapped held-out openings; 384 games per generation, 0.10 s per move, one CPU core.",
        "credit": "Generated from experiment JSON"
      },
      "notes": "With architecture, held-out openings, and time controls fixed, generation 3 has the highest observed score.\n\nTeacher iteration improves the small H16 model; generation 3 reaches 70.18% under one protocol.",
      "sources": [
        "trainnnue/iter3_experiment.json",
        "trainnnue/iteration_vs_pst.svg",
        "trainnnue/run_teacher_iteration.ps1"
      ],
      "takeaway": "Teacher iteration improves the small H16 model; generation 3 reaches 70.18% under one protocol."
    },
    {
      "id": "e14g",
      "eyebrow": "External benchmark · Official Pikafish NNUE",
      "title": "Above Pikafish's built-in 1900 setting",
      "layout": "figure",
      "lead": "On 360 held-out color-swapped games, our NNUE scores 56.39%; full-strength Pikafish shows the remaining gap.",
      "figure": {
        "src": "assets/nnue/external-benchmark.svg",
        "alt": "Our NNUE scores 56.39% against official Pikafish UCI Elo 1900 and 7.78% against full strength.",
        "caption": "Official Pikafish 2026-01-31; 180 formal openings, each color-swapped, 360 games.",
        "credit": "Per-game JSON and paired bootstrap"
      },
      "notes": "On 360 held-out color-swapped games, our NNUE scores 56.39%; full-strength Pikafish shows the remaining gap.\n\nOur NNUE exceeds Pikafish's built-in 1900 setting, with a large gap to full strength.",
      "sources": [
        "trainnnue/iter2_vs_pikafish_elo1900_180pairs.json",
        "trainnnue/iter2_vs_pikafish_official_180pairs.json",
        "trainnnue/run_external_match.ps1"
      ],
      "takeaway": "Our NNUE exceeds Pikafish's built-in 1900 setting, with a large gap to full strength."
    },
    {
      "id": "e18a",
      "eyebrow": "The AlphaGo approach · How it works",
      "title": "Policy guides, value evaluates, the tree backs up results",
      "layout": "figure",
      "lead": "CNNs scan local board windows and combine features across layers; each new leaf's output guides subsequent tree visits.",
      "figure": {
        "src": "assets/alphago/alphago-policy-value-search.svg",
        "alt": "The full board enters policy and value CNNs; policy supplies move priors, value evaluates leaves, and tree backup guides branch selection.",
        "caption": "Redrawn from 2016 AlphaGo, Figs. 1b and 3; that version combines value predictions with fast rollouts.",
        "credit": "Silver et al. · Nature 2016"
      },
      "steps": [
        "Policy: prioritize legal moves and guide the tree.",
        "Value: estimate a new leaf's outcome prospects.",
        "Back up evaluations so stronger branches receive more visits."
      ],
      "notes": "CNNs scan local board windows and combine features across layers; each new leaf's output guides subsequent tree visits.\n\nPolicy: prioritize legal moves and guide the tree.\n\nValue: estimate a new leaf's outcome prospects.\n\nBack up evaluations so stronger branches receive more visits.\n\nPolicy and value guide the tree with richer, more expensive full-board inference at new leaves.",
      "sources": [
        "https://deepmind-media.storage.googleapis.com/alphago/AlphaGoNaturePaper.pdf"
      ],
      "takeaway": "Policy and value guide the tree with richer, more expensive full-board inference at new leaves."
    },
    {
      "id": "e18",
      "eyebrow": "Two neural approaches · A direct comparison",
      "title": "Why is NNUE cheaper inside this CPU searcher?",
      "layout": "table",
      "lead": "Incremental evaluation leaves more CPU time for exploring continuations.",
      "table": {
        "headers": [
          "Approach",
          "Reuse between adjacent positions",
          "Cost of a new node",
          "Effect under fixed time"
        ],
        "rows": [
          [
            "NNUE + traditional search",
            "Subtract old features, add new ones; reuse the first-layer accumulator",
            "Low CPU latency, followed by a small output network",
            "Evaluate many nodes and search deeper"
          ],
          [
            "AlphaGo-style CNN + MCTS",
            "Run full-board convolution at each new leaf; cache results in the tree",
            "Heavier leaf inference; the original system used asynchronous GPUs",
            "Fewer new leaves; policy priors focus visits on promising branches"
          ]
        ]
      },
      "cards": [
        {
          "title": "Pikafish Wiki · 2025-01-06",
          "text": "The wiki reports that CPU engines remain stronger than GPU engines in Xiangqi."
        }
      ],
      "steps": [
        "NNUE caches the expensive first layer, updates changed features, and runs small later layers.",
        "An AlphaGo-style CNN performs multilayer full-board inference at each new leaf.",
        "On the same CPU budget, heavier nodes mean fewer replies explored and less reachable depth."
      ],
      "notes": "Incremental evaluation leaves more CPU time for exploring continuations.\n\nNNUE caches the expensive first layer, updates changed features, and runs small later layers.\n\nAn AlphaGo-style CNN performs multilayer full-board inference at each new leaf.\n\nOn the same CPU budget, heavier nodes mean fewer replies explored and less reachable depth.\n\nPikafish Wiki · 2025-01-06: The wiki reports that CPU engines remain stronger than GPU engines in Xiangqi.\n\nNNUE spends the budget on more nodes; the AlphaGo approach uses richer guidance per leaf.",
      "sources": [
        "https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html",
        "https://deepmind-media.storage.googleapis.com/alphago/AlphaGoNaturePaper.pdf",
        "https://www.pikafish.com/wiki/index.php?oldid=482&title=象棋有“阿尔法狗”吗？"
      ],
      "takeaway": "NNUE spends the budget on more nodes; the AlphaGo approach uses richer guidance per leaf."
    },
    {
      "id": "e11",
      "eyebrow": "Evaluation · Selecting the current version",
      "title": "What do we use after these experiments?",
      "layout": "table",
      "lead": "Keep PST as a transparent baseline; deploy the trained and validated NNUE as the default upgrade.",
      "table": {
        "headers": [
          "Option",
          "Project result",
          "Current use"
        ],
        "rows": [
          [
            "Material only",
            "Piece types and counts; incremental O(1) updates",
            "Simplest evaluation baseline"
          ],
          [
            "PST",
            "Fast, interpretable ElephantEye tables adjusted through practice",
            "Keep as the project PST engine and comparison baseline"
          ],
          [
            "Piece relationships",
            "The attempted features made execution several times slower",
            "Removed"
          ],
          [
            "Project NNUE",
            "D3/D4 training and three NNUE+D3 teacher iterations completed",
            "Iter2 peaks at 70.18%; deployed in the web demo"
          ]
        ]
      },
      "steps": [
        "Explicit relationship terms added information but cost several times more runtime.",
        "PST remains interpretable and makes neural gains measurable.",
        "Iter2 has the highest observed score across three teacher iterations; deploy.ps1 updates the demo."
      ],
      "notes": "Keep PST as a transparent baseline; deploy the trained and validated NNUE as the default upgrade.\n\nExplicit relationship terms added information but cost several times more runtime.\n\nPST remains interpretable and makes neural gains measurable.\n\nIter2 has the highest observed score across three teacher iterations; deploy.ps1 updates the demo.\n\nPST is the transparent baseline; NNUE is the validated default. Evaluate both with search cost.",
      "sources": [
        "xiangqi_ai.cpp:791",
        "trainnnue/nnue_engine.cpp",
        "trainnnue/direct_match_summary.json",
        "trainnnue/RESULTS.generated.md"
      ],
      "takeaway": "PST is the transparent baseline; NNUE is the validated default. Evaluate both with search cost."
    },
    {
      "id": "e19",
      "eyebrow": "Stage 2 complete",
      "title": "We have intuition, but not foresight",
      "layout": "cards",
      "lead": "Neither PST nor search-distilled NNUE replaces explicit consideration of replies.",
      "cards": [
        {
          "title": "What we have",
          "text": "Two evaluators: fast, transparent PST and incremental NNUE that learns relationships."
        },
        {
          "title": "What is missing",
          "text": "How will the opponent reply? Will a captured piece immediately be recaptured?"
        },
        {
          "title": "Stage 3",
          "text": "Expand moves into a tree and test intuition against both players' choices."
        }
      ],
      "steps": [
        "Evaluation measures positions reached by search.",
        "Search determines which positions can actually arise."
      ],
      "notes": "Neither PST nor search-distilled NNUE replaces explicit consideration of replies.\n\nEvaluation measures positions reached by search.\n\nSearch determines which positions can actually arise.\n\nWhat we have: Two evaluators: fast, transparent PST and incremental NNUE that learns relationships.\n\nWhat is missing: How will the opponent reply? Will a captured piece immediately be recaptured?\n\nStage 3: Expand moves into a tree and test intuition against both players' choices.\n\nEvaluation scores leaves; search tests those scores against concrete replies.",
      "sources": [
        "xiangqi_ai.cpp:791",
        "trainnnue/nnue_engine.cpp",
        "xiangqi_ai.cpp:1123"
      ],
      "takeaway": "Evaluation scores leaves; search tests those scores against concrete replies."
    }
  ]
});
