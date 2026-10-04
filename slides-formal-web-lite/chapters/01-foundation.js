window.XQ_CHAPTERS = window.XQ_CHAPTERS || [];
window.XQ_CHAPTERS.push({
  "id": "01",
  "title": "Making legal moves",
  "slides": [
    {
      "id": "f01",
      "title": "Can a computer help me play?",
      "eyebrow": "A personal starting point",
      "layout": "cards",
      "lead": "I calculate slowly and my intuition is unreliable. Computers calculate quickly.",
      "cards": [
        {
          "title": "Me",
          "text": "Beginner levels 1–3 on Tiantian Xiangqi; I often miss variations."
        },
        {
          "title": "The computer",
          "text": "It knows no chess, but repeats calculations very quickly."
        },
        {
          "title": "Our task",
          "text": "Break playing chess into skills and teach them one by one."
        }
      ],
      "steps": [
        "Humans lose track; computers excel at repeated calculations.",
        "Separate the skills of playing chess so we can implement each one.",
        "Today we build a Xiangqi partner from scratch."
      ],
      "notes": "I calculate slowly and my intuition is unreliable. Computers calculate quickly.\n\nHumans lose track; computers excel at repeated calculations.\n\nSeparate the skills of playing chess so we can implement each one.\n\nToday we build a Xiangqi partner from scratch.\n\nMe: Beginner levels 1–3 on Tiantian Xiangqi; I often miss variations.\n\nThe computer: It knows no chess, but repeats calculations very quickly.\n\nOur task: Break playing chess into skills and teach them one by one.\n\nStart by asking which skills a chess engine needs.",
      "sources": [
        "Original presentation PDF P2"
      ],
      "takeaway": "Start by asking which skills a chess engine needs."
    },
    {
      "id": "f02",
      "title": "Teach the computer the skills we use",
      "eyebrow": "The roadmap",
      "layout": "map",
      "currentChapter": 0,
      "lead": "First legal moves, then position evaluation, then forward search.",
      "steps": [
        "Move: represent the board, generate candidates, and check legality.",
        "Evaluate: turn a position into a comparable score.",
        "Search: consider replies and remember previously searched positions."
      ],
      "notes": "First legal moves, then position evaluation, then forward search.\n\nMove: represent the board, generate candidates, and check legality.\n\nEvaluate: turn a position into a comparable score.\n\nSearch: consider replies and remember previously searched positions.\n\nThree stages: moves, evaluation, search.",
      "sources": [
        "Original presentation PDF P3"
      ],
      "takeaway": "Three stages: moves, evaluation, search."
    },
    {
      "id": "f03",
      "title": "How does a computer represent the board?",
      "eyebrow": "Moves · Board state",
      "layout": "compare",
      "lead": "We see a board; the computer needs a readable, writable position.",
      "boards": [
        {
          "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
          "caption": "Initial position, Red to move (row 0 at top, row 9 at bottom)",
          "highlights": [
            {
              "square": "e0",
              "kind": "focus"
            },
            {
              "square": "e9",
              "kind": "focus"
            }
          ],
          "arrows": [],
          "annotations": []
        }
      ],
      "cards": [
        {
          "title": "board[10][9]",
          "text": "One character per square: uppercase Red, lowercase Black, dot for empty."
        },
        {
          "title": "turn",
          "text": "The side to move is part of the position, even when the board is identical."
        }
      ],
      "code": "board[9][4] = 'K';  // Red king at (9,4)\nboard[0][4] = 'k';  // Black king at (0,4)\nturn = RED;          // Red to move",
      "steps": [
        "Store every square in a 10×9 character array.",
        "The side to move is an essential part of a position."
      ],
      "notes": "We see a board; the computer needs a readable, writable position.\n\nStore every square in a 10×9 character array.\n\nThe side to move is an essential part of a position.\n\nboard[10][9]: One character per square: uppercase Red, lowercase Black, dot for empty.\n\nturn: The side to move is part of the position, even when the board is identical.\n\nPosition = 10×9 board + side to move.",
      "sources": [
        "Original presentation PDF P5",
        "xiangqi_ai.cpp:291",
        "xiangqi_ai.cpp:390"
      ],
      "takeaway": "Position = 10×9 board + side to move."
    },
    {
      "id": "f04",
      "title": "A move needs a source and a destination",
      "eyebrow": "Moves · Actions",
      "layout": "board",
      "lead": "Where does the piece start, and where does it finish?",
      "boards": [
        {
          "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
          "caption": "Red to move: central cannon, (7,7) → (7,4)",
          "highlights": [
            {
              "square": "h7",
              "kind": "from"
            },
            {
              "square": "e7",
              "kind": "to"
            }
          ],
          "arrows": [
            {
              "from": "h7",
              "to": "e7",
              "kind": "primary"
            }
          ],
          "annotations": []
        }
      ],
      "code": "Move m = {7, 7, 7, 4};\n// (r1,c1) = (7,7)  source\n// (r2,c2) = (7,4)  destination",
      "steps": [
        "The source identifies the moving piece.",
        "The destination identifies its target square.",
        "Two row/column pairs give four numbers per move."
      ],
      "notes": "Where does the piece start, and where does it finish?\n\nThe source identifies the moving piece.\n\nThe destination identifies its target square.\n\nTwo row/column pairs give four numbers per move.\n\nA move is an operation from one square to another.",
      "sources": [
        "Original presentation PDF P5",
        "xiangqi_ai.cpp:48"
      ],
      "takeaway": "A move is an operation from one square to another."
    },
    {
      "id": "f05",
      "title": "Where can this horse move?",
      "eyebrow": "Moves · Candidates",
      "layout": "board",
      "lead": "Apply the piece's own rules to list possible destinations.",
      "boards": [
        {
          "fen": "4k4/9/9/9/4P4/4N4/9/9/9/4K4 w",
          "caption": "Red horse at (5,4); the pawn at (4,4) blocks its upward leg",
          "highlights": [
            {
              "square": "e5",
              "kind": "from"
            },
            {
              "square": "e4",
              "kind": "blocked"
            },
            {
              "square": "c4",
              "kind": "candidate"
            },
            {
              "square": "c6",
              "kind": "candidate"
            },
            {
              "square": "d7",
              "kind": "candidate"
            },
            {
              "square": "f7",
              "kind": "candidate"
            },
            {
              "square": "g4",
              "kind": "candidate"
            },
            {
              "square": "g6",
              "kind": "candidate"
            }
          ],
          "arrows": [
            {
              "from": "e5",
              "to": "d3",
              "kind": "blocked"
            },
            {
              "from": "e5",
              "to": "f3",
              "kind": "blocked"
            }
          ],
          "annotations": [
            {
              "square": "e4",
              "text": "Blocked leg"
            }
          ]
        }
      ],
      "steps": [
        "The eight L-shaped destinations are only initial candidates.",
        "The pawn at (4,4) rules out (3,3) and (3,5).",
        "Check the remaining targets for board boundaries and friendly pieces."
      ],
      "notes": "Apply the piece's own rules to list possible destinations.\n\nThe eight L-shaped destinations are only initial candidates.\n\nThe pawn at (4,4) rules out (3,3) and (3,5).\n\nCheck the remaining targets for board boundaries and friendly pieces.\n\nCandidates depend on movement, boundaries, blockers, and ownership.",
      "sources": [
        "Original presentation PDF P6",
        "xiangqi_ai.cpp:669"
      ],
      "takeaway": "Candidates depend on movement, boundaries, blockers, and ownership."
    },
    {
      "id": "f06",
      "title": "Seven pieces, seven sets of local rules",
      "eyebrow": "Moves · Translating rules",
      "layout": "table",
      "lead": "This layer asks where each piece can move under its own rules.",
      "table": {
        "headers": [
          "Piece",
          "Key conditions"
        ],
        "rows": [
          [
            "Rook",
            "Along a rank or file up to the first blocker"
          ],
          [
            "Cannon",
            "Straight quiet moves; exactly one screen for a capture"
          ],
          [
            "Horse",
            "L-shaped move; the adjacent leg square must be empty"
          ],
          [
            "Elephant",
            "Two diagonal steps; clear eye; cannot cross the river"
          ],
          [
            "Advisor",
            "One diagonal step inside the palace"
          ],
          [
            "King",
            "One orthogonal step inside the palace; kings must not face"
          ],
          [
            "Pawn",
            "Forward only; sideways allowed after crossing the river"
          ]
        ]
      },
      "steps": [
        "Each piece has its own local reachability conditions.",
        "A locally valid move may still be illegal for the position."
      ],
      "notes": "This layer asks where each piece can move under its own rules.\n\nEach piece has its own local reachability conditions.\n\nA locally valid move may still be illegal for the position.\n\nPiece rules generate candidates; king safety determines legality.",
      "sources": [
        "Original presentation PDF P6",
        "xiangqi_ai.cpp:677"
      ],
      "takeaway": "Piece rules generate candidates; king safety determines legality."
    },
    {
      "id": "f07",
      "title": "Iterate only over pieces that exist",
      "eyebrow": "Moves · Piece lists",
      "layout": "compare",
      "lead": "The board stores pieces; two-way indices locate pieces and list slots.",
      "cards": [
        {
          "title": "piece_sq[side][slot]",
          "text": "List slot → square; npieces is the active list length."
        },
        {
          "title": "piece_idx[row][column]",
          "text": "Square → list slot, for direct updates during moves and captures."
        },
        {
          "title": "Piece type",
          "text": "Read the type from board[row][column]; coordinates distinguish identical pieces."
        }
      ],
      "steps": [
        "Scan the board once at initialization and populate each side's list.",
        "Generate moves by visiting only the first npieces entries.",
        "An ordinary move updates its slot and both square-to-slot references."
      ],
      "notes": "The board stores pieces; two-way indices locate pieces and list slots.\n\nScan the board once at initialization and populate each side's list.\n\nGenerate moves by visiting only the first npieces entries.\n\nAn ordinary move updates its slot and both square-to-slot references.\n\npiece_sq[side][slot]: List slot → square; npieces is the active list length.\n\npiece_idx[row][column]: Square → list slot, for direct updates during moves and captures.\n\nPiece type: Read the type from board[row][column]; coordinates distinguish identical pieces.\n\nTwo-way indices support fast iteration and direct updates.",
      "sources": [
        "Original presentation PDF P5–6",
        "xiangqi_ai.cpp:308-311",
        "xiangqi_ai.cpp:450-469",
        "xiangqi_ai.cpp:507-530",
        "xiangqi_ai.cpp:771"
      ],
      "takeaway": "Two-way indices support fast iteration and direct updates."
    },
    {
      "id": "f07a",
      "title": "How do captures avoid holes in the list?",
      "eyebrow": "Moves · Swap removal",
      "layout": "table",
      "lead": "Fill the captured piece's slot with the last entry; undo restores the original slot.",
      "table": {
        "headers": [
          "Stage",
          "npieces",
          "Slots 0 / 1 / 2 / 3 (piece names for readability)",
          "Reverse index"
        ],
        "rows": [
          [
            "Before capture",
            "4",
            "(0,4) K / (2,1) C / (2,7) C / (3,0) P",
            "(2,1)→1；(3,0)→3"
          ],
          [
            "Capture cannon in slot 1",
            "3",
            "(0,4) K / (3,0) P / (2,7) C / inactive",
            "(3,0)→1; save original slot 1"
          ],
          [
            "Undo: restore last entry",
            "4",
            "(0,4) K / (3,0) P / (2,7) C / (3,0) P",
            "(3,0)→3"
          ],
          [
            "Undo: restore cannon",
            "4",
            "(0,4) K / (2,1) C / (2,7) C / (3,0) P",
            "(2,1)→1；(3,0)→3"
          ]
        ]
      },
      "cards": [
        {
          "title": "A memory operation",
          "text": "The pawn's record moves from slot 3 to slot 1; the pawn stays at (3,0)."
        },
        {
          "title": "Boundary case",
          "text": "If the captured piece is last, simply shorten the active list."
        }
      ],
      "steps": [
        "Save the captured piece's original slot: 1.",
        "Copy (3,0) from slot 3 into slot 1; update its reverse index to 1.",
        "npieces decreases from 4 to 3, keeping iteration contiguous.",
        "Undo moves the replacement back to slot 3 and restores the cannon in slot 1."
      ],
      "notes": "Fill the captured piece's slot with the last entry; undo restores the original slot.\n\nSave the captured piece's original slot: 1.\n\nCopy (3,0) from slot 3 into slot 1; update its reverse index to 1.\n\nnpieces decreases from 4 to 3, keeping iteration contiguous.\n\nUndo moves the replacement back to slot 3 and restores the cannon in slot 1.\n\nA memory operation: The pawn's record moves from slot 3 to slot 1; the pawn stays at (3,0).\n\nBoundary case: If the captured piece is last, simply shorten the active list.\n\nSwap removal keeps lists compact; saved slots make undo exact.",
      "sources": [
        "xiangqi_ai.cpp:507-530",
        "xiangqi_ai.cpp:575-600"
      ],
      "takeaway": "Swap removal keeps lists compact; saved slots make undo exact."
    },
    {
      "id": "f08",
      "title": "Try making a move",
      "eyebrow": "Moves · make_move",
      "layout": "compare",
      "lead": "A trial move changes the position and remembers the captured piece.",
      "boards": [
        {
          "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
          "caption": "Before: Red to move, right cannon at (7,7)",
          "highlights": [
            {
              "square": "h7",
              "kind": "from"
            },
            {
              "square": "h0",
              "kind": "capture"
            }
          ],
          "arrows": [
            {
              "from": "h7",
              "to": "h0",
              "kind": "capture"
            }
          ],
          "annotations": []
        },
        {
          "fen": "rnbakabCr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C7/9/RNBAKABNR b",
          "caption": "After: Red cannon captures the horse at (0,7), using (2,7) as a screen; Black to move",
          "highlights": [
            {
              "square": "h7",
              "kind": "from"
            },
            {
              "square": "h0",
              "kind": "to"
            }
          ],
          "arrows": [],
          "annotations": [
            {
              "square": "h2",
              "text": "Screen"
            }
          ]
        }
      ],
      "steps": [
        "The cannon moves from (7,7), over the screen at (2,7), to the horse at (0,7).",
        "The source becomes empty, the target holds the red cannon, and Black moves next.",
        "make_move returns the captured horse so the move can be undone."
      ],
      "notes": "A trial move changes the position and remembers the captured piece.\n\nThe cannon moves from (7,7), over the screen at (2,7), to the horse at (0,7).\n\nThe source becomes empty, the target holds the red cannon, and Black moves next.\n\nmake_move returns the captured horse so the move can be undone.\n\nmake_move updates the position and retains the information needed for undo.",
      "sources": [
        "Original presentation PDF P7",
        "xiangqi_ai.cpp:485"
      ],
      "takeaway": "make_move updates the position and retains the information needed for undo."
    },
    {
      "id": "f09",
      "title": "Why undo a move immediately?",
      "eyebrow": "Moves · undo_move",
      "layout": "cards",
      "lead": "The engine repeatedly explores hypothetical moves.",
      "cards": [
        {
          "title": "1. make",
          "text": "Try a candidate, obtain a new position, and remember any capture."
        },
        {
          "title": "2. inspect",
          "text": "Check legality; later, search further from this position."
        },
        {
          "title": "3. undo",
          "text": "Restore source, target, capture, turn, and all incremental state."
        },
        {
          "title": "4. next",
          "text": "Return to exactly the original state before trying another candidate."
        }
      ],
      "steps": [
        "Making a move enters a hypothetical future.",
        "Inspect that future for legality or further variations.",
        "Undo restores every state component before the next candidate."
      ],
      "notes": "The engine repeatedly explores hypothetical moves.\n\nMaking a move enters a hypothetical future.\n\nInspect that future for legality or further variations.\n\nUndo restores every state component before the next candidate.\n\n1. make: Try a candidate, obtain a new position, and remember any capture.\n\n2. inspect: Check legality; later, search further from this position.\n\n3. undo: Restore source, target, capture, turn, and all incremental state.\n\n4. next: Return to exactly the original state before trying another candidate.\n\nThe basic exploration loop is make → inspect → undo.",
      "sources": [
        "Original presentation PDF P7",
        "xiangqi_ai.cpp:552"
      ],
      "takeaway": "The basic exploration loop is make → inspect → undo."
    },
    {
      "id": "f10",
      "title": "A piece can move there. Is the move legal?",
      "eyebrow": "Moves · Pseudo-legal vs legal",
      "layout": "board",
      "lead": "A sideways pawn move may obey its local rule but expose the two kings.",
      "boards": [
        {
          "fen": "4k4/9/9/9/4P4/9/9/9/9/4K4 w",
          "caption": "Red to move: (4,4)→(4,3) exposes the facing kings",
          "highlights": [
            {
              "square": "e4",
              "kind": "from"
            },
            {
              "square": "d4",
              "kind": "candidate"
            },
            {
              "square": "e3",
              "kind": "candidate"
            },
            {
              "square": "e0",
              "kind": "danger"
            },
            {
              "square": "e9",
              "kind": "danger"
            }
          ],
          "arrows": [
            {
              "from": "e4",
              "to": "d4",
              "kind": "blocked"
            },
            {
              "from": "e4",
              "to": "e3",
              "kind": "primary"
            },
            {
              "from": "e0",
              "to": "e9",
              "kind": "danger",
              "fragmentIndex": 1
            }
          ],
          "annotations": [
            {
              "square": "e4",
              "text": "Only blocker"
            }
          ]
        }
      ],
      "steps": [
        "After crossing the river, the pawn may locally move (4,4)→(4,3).",
        "Moving sideways leaves no piece between the kings.",
        "(4,4)→(4,3) is pseudo-legal but illegal; (4,4)→(3,4) keeps the file blocked and is legal."
      ],
      "notes": "A sideways pawn move may obey its local rule but expose the two kings.\n\nAfter crossing the river, the pawn may locally move (4,4)→(4,3).\n\nMoving sideways leaves no piece between the kings.\n\n(4,4)→(4,3) is pseudo-legal but illegal; (4,4)→(3,4) keeps the file blocked and is legal.\n\nLocal piece movement alone does not establish position legality.",
      "sources": [
        "Original presentation PDF P8",
        "xiangqi_ai.cpp:735",
        "xiangqi_ai.cpp:793"
      ],
      "takeaway": "Local piece movement alone does not establish position legality."
    },
    {
      "id": "f11",
      "title": "A simple, reliable legality check",
      "eyebrow": "Moves · Make, check, undo",
      "layout": "code",
      "lead": "Create the candidate position, then check the moving side's king.",
      "code": "const bool red_mover = (turn == 0);  // Save the moving side\nstd::vector<Move> legal_moves;\nfor (Move m : pseudo_moves) {\n  char captured = make_move(m);\n  bool legal = !is_in_check(red_mover);\n  undo_move(m, captured);\n  if (legal) legal_moves.push_back(m);\n}",
      "cards": [
        {
          "title": "Make",
          "text": "Put the board into the candidate position."
        },
        {
          "title": "Check",
          "text": "Test enemy rook, cannon, horse, pawn, and king attacks on our king."
        },
        {
          "title": "Always undo",
          "text": "Return to the same starting position whether the move is legal or not."
        }
      ],
      "steps": [
        "Make the move to create the candidate position.",
        "Check whether our king is under attack.",
        "Always undo; retain only candidates that leave our king safe."
      ],
      "notes": "Create the candidate position, then check the moving side's king.\n\nMake the move to create the candidate position.\n\nCheck whether our king is under attack.\n\nAlways undo; retain only candidates that leave our king safe.\n\nMake: Put the board into the candidate position.\n\nCheck: Test enemy rook, cannon, horse, pawn, and king attacks on our king.\n\nAlways undo: Return to the same starting position whether the move is legal or not.\n\nPseudo-legal moves become legal after make → check → undo.",
      "sources": [
        "Original presentation PDF P8",
        "xiangqi_ai.cpp:793",
        "xiangqi_ai.cpp:1381"
      ],
      "takeaway": "Pseudo-legal moves become legal after make → check → undo."
    },
    {
      "id": "f12",
      "title": "Why cache the king positions?",
      "eyebrow": "Moves · Frequent queries",
      "layout": "compare",
      "lead": "Every trial move checks king safety; repeatedly locating the king wastes work.",
      "cards": [
        {
          "title": "Find it again",
          "text": "Scan 90 squares, then check attacks."
        },
        {
          "title": "Keep it cached",
          "text": "king_pos[2] stores both kings; update on king moves, captures, and undo."
        },
        {
          "title": "The same pattern",
          "text": "Piece lists also retain answers to frequent queries in state."
        }
      ],
      "steps": [
        "Scanning 90 squares before every check repeats the same work.",
        "king_pos changes only when the king position changes.",
        "Piece lists and king positions are indices for frequent queries."
      ],
      "notes": "Every trial move checks king safety; repeatedly locating the king wastes work.\n\nScanning 90 squares before every check repeats the same work.\n\nking_pos changes only when the king position changes.\n\nPiece lists and king positions are indices for frequent queries.\n\nFind it again: Scan 90 squares, then check attacks.\n\nKeep it cached: king_pos[2] stores both kings; update on king moves, captures, and undo.\n\nThe same pattern: Piece lists also retain answers to frequent queries in state.\n\nMaintain frequent-query answers incrementally through make/undo.",
      "sources": [
        "Original presentation PDF P5–8",
        "xiangqi_ai.cpp:299",
        "xiangqi_ai.cpp:490"
      ],
      "takeaway": "Maintain frequent-query answers incrementally through make/undo."
    },
    {
      "id": "f13",
      "title": "No legal moves means the game is over",
      "eyebrow": "Moves · Terminal conditions",
      "layout": "cards",
      "lead": "Checkmate and stalemate share one question: does the moving side have any legal move?",
      "cards": [
        {
          "title": "In check + no legal move",
          "text": "Checkmate: the side to move loses."
        },
        {
          "title": "Not in check + no legal move",
          "text": "Stalemate: the side to move also loses in Xiangqi."
        },
        {
          "title": "One engine interface",
          "text": "Generate and filter candidates; zero legal moves means a loss."
        }
      ],
      "steps": [
        "In check with no legal move is checkmate.",
        "Not in check with no legal move is stalemate.",
        "Both are losses for the side to move in Xiangqi."
      ],
      "notes": "Checkmate and stalemate share one question: does the moving side have any legal move?\n\nIn check with no legal move is checkmate.\n\nNot in check with no legal move is stalemate.\n\nBoth are losses for the side to move in Xiangqi.\n\nIn check + no legal move: Checkmate: the side to move loses.\n\nNot in check + no legal move: Stalemate: the side to move also loses in Xiangqi.\n\nOne engine interface: Generate and filter candidates; zero legal moves means a loss.\n\nZero legal moves ends the game; both mate and stalemate are losses.",
      "sources": [
        "xiangqi_ai.cpp:1250",
        "xiangqi_ai.cpp:1516",
        "webapp.py:115"
      ],
      "takeaway": "Zero legal moves ends the game; both mate and stalemate are losses."
    },
    {
      "id": "f14",
      "title": "We have built a world with rules",
      "eyebrow": "Stage 1 complete",
      "layout": "map",
      "currentChapter": 0,
      "lead": "We can now try every legal option. Next, decide which options are better.",
      "steps": [
        "Represent positions and propose candidates using piece rules.",
        "Filter legal moves through make, check, and undo.",
        "It cannot choose well yet, but it can move legally."
      ],
      "notes": "We can now try every legal option. Next, decide which options are better.\n\nRepresent positions and propose candidates using piece rules.\n\nFilter legal moves through make, check, and undo.\n\nIt cannot choose well yet, but it can move legally.\n\nFirst skill unlocked: legal moves.",
      "sources": [
        "Original presentation PDF P4–8"
      ],
      "takeaway": "First skill unlocked: legal moves."
    },
    {
      "id": "f15",
      "title": "All are legal. Which is better?",
      "eyebrow": "Next: position evaluation",
      "layout": "compare",
      "lead": "Legality rejects impossible moves; the remaining moves still need comparison.",
      "cards": [
        {
          "title": "Candidate A",
          "text": "Legal, but may lose material or worsen the position."
        },
        {
          "title": "Candidate B",
          "text": "Also legal, but may gain material or improve placement."
        },
        {
          "title": "The next question",
          "text": "How can position quality become a comparable score?"
        }
      ],
      "steps": [
        "The rules layer retains every legal candidate.",
        "Legal candidates can differ greatly in quality.",
        "An evaluation function lets the program compare positions."
      ],
      "notes": "Legality rejects impossible moves; the remaining moves still need comparison.\n\nThe rules layer retains every legal candidate.\n\nLegal candidates can differ greatly in quality.\n\nAn evaluation function lets the program compare positions.\n\nCandidate A: Legal, but may lose material or worsen the position.\n\nCandidate B: Also legal, but may gain material or improve placement.\n\nThe next question: How can position quality become a comparable score?\n\nRules establish legality; evaluation distinguishes quality.",
      "sources": [
        "Original presentation PDF P9–10",
        "xiangqi_ai.cpp:91-106"
      ],
      "takeaway": "Rules establish legality; evaluation distinguishes quality."
    }
  ]
});
