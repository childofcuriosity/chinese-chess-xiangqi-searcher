window.XQ_CHAPTERS = window.XQ_CHAPTERS || [];
const MEMORY_START = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR';
const MEMORY_RED_HORSE = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1CN4C1/9/R1BAKABNR';
const MEMORY_FOUR_HORSES = 'r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/9/P1P1P1P1P/1CN3NC1/9/R1BAKAB1R';
const MEMORY_CAPTURE_BEFORE = '5k3/9/9/9/4p4/4P4/9/9/9/3K5';
const MEMORY_CAPTURE_AFTER = '5k3/9/9/9/4P4/9/9/9/9/3K5';
window.XQ_CHAPTERS.push({
  id: '04',
  title: '向前推演：先算明白',
  slides: [
    {
      id: 's01', title: '我们已经会评分，却还不会下棋', eyebrow: '第三阶段 · 向前推演', layout: 'map',
      lead: '棋盘、规则和评分函数都有了。下一步：把对手的回答放进自己的思考。',
      cards: [
        {title: '已经会', text: '生成合法着、试走与悔棋、对叶子局面打分'},
        {title: '还不会', text: '理解对手会专门选让我们难受的应手'},
        {title: '本章问题', text: '如何在有限时间里，尽量把对手的反击算明白'}
      ],
      steps: ['先看一层：枚举我方所有候选着', '再多看一层：对手也会选', '最后面对现实：树太大，时间会到'],
      notes: '前面两个阶段，我们给电脑造了棋盘，教它守规则，还给了一个局面评分函数。但评分高，不等于这手就好。【按键】因为棋不会在我们走完以后停住。【停顿】第三阶段的主角是一棵不断向下生长的树。我们先教它老老实实算明白，再教它哪些地方可以不算完。',
      sources: ['xiangqi_ai.cpp:1123'], takeaway: '搜索把局面评分放进双方轮流选择的推演过程。'
    },
    {
      id: 's02', title: '最朴素的办法：每一手都试走', eyebrow: '试走与回退 · 枚举', layout: 'board',
      lead: '生成候选着 → 走一步 → 评分 → 悔棋 → 试下一手。',
      boards: [{
        fen: 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w', caption: '初始局面：红方候选着示意',
        highlights: [{square:'b9',kind:'from'},{square:'a7',kind:'to'},{square:'c7',kind:'to'},{square:'e6',kind:'from'},{square:'e5',kind:'to'}],
        arrows: [{from:'b9',to:'a7',kind:'move'},{from:'b9',to:'c7',kind:'move'},{from:'e6',to:'e5',kind:'move'}], annotations: []
      }],
      code: `best = -INF\nfor move in legal_moves:\n  captured = make(move)\n  score = evaluate()\n  undo(move, captured)\n  best = max(best, score)`,
      steps: ['候选着是一组可试验的假设', '每次 make 之后评分', '每次 undo 之后回到同一起点'],
      notes: '先从第一版最自然的办法开始：把每一手合法棋都试一遍。【按键】图上示意几个候选：边马可以跳到两个空位，中兵可以向前一步。【按键】选一手走下去，用前面做好的函数评分，然后悔棋，再试下一手。【按键】每个候选都必须从同一个原局面出发；make 改了哪些棋子和轮次，undo 就要逐项恢复。',
      sources: ['xiangqi_ai.cpp:669','xiangqi_ai.cpp:485','xiangqi_ai.cpp:552'], takeaway: '搜索的第一步，是把走法变成可撤销的假设。'
    },
    {
      id: 's03', title: '只看自己走完的分数，会贪心', eyebrow: '第一次失败', layout: 'cards',
      lead: '眼前吃到了子，不代表对手下一手拿不回去。',
      cards: [
        {title: '机器的旧逻辑', text: '我走完以后，哪个局面分数高，就选哪个'},
        {title: '棋局的现实', text: '接下来轮到对手，而且对手会专门选我们最不愿意看到的回答'},
        {title: '需要的新能力', text: '不只试走自己一步，还要继续枚举对手的应手'}
      ],
      steps: ['我方会选眼前评分更高的候选', '加入对手应手后，得分可能立即反转', '下一层轮到对手选，它会选我方最不利的应手'],
      notes: '当我们只评分自己走完的局面，机器会偏爱眼前最高分。【按键】一展开对手的应手，这个便宜很可能立即被拿回去。【停顿，看向听众】下一层轮到谁选择？轮到对手，它会挑对我们最不利的一手。',
      sources: ['xiangqi_ai.cpp:1123'], takeaway: '轮到对手时，它会选择对我们最不利的应手。'
    },
    {
      id: 's04', title: '固定分数视角：红方选大，黑方选小', eyebrow: '双方轮流选择 · Minimax', layout: 'tree',
      lead: '全章分数始终以红方为正：轮到红方取最大值，轮到黑方取最小值。',
      tree: {kind:'minimax', values:[4,-2,1,3], stage:1, caption:'4 / -2 / 1 / 3 均为教学分，不对应真实棋局'},
      steps: ['四个叶子的数字都是红方视角教学分', '黑方层分别取 min(4,-2)=-2 和 min(1,3)=1', '红方根节点取 max(-2,1)=1'],
      notes: '先固定分数刻度：正分对红方有利，负分对黑方有利，与引擎实际执红还是执黑无关。【按键】左边轮到黑方，它在 4 和 -2 中选更小的 -2；右边也由黑方在 1 和 3 中选 1。【按键】回到红方，它在 -2 和 1 中选更大的 1。Minimax 就这样让双方都选择对自己最有利的分支，再把叶子分数逐层传回根节点。',
      sources: ['xiangqi_ai.cpp:1123','xiangqi_ai.cpp:1409'], takeaway: 'Minimax 把“对手也会做最佳选择”写进递归。'
    },
    {
      id: 's05', title: '同一段逻辑，一层层重复', eyebrow: '递归骨架', layout: 'code',
      lead: '走子、换方、向下搜、悔棋；只有“谁选大、谁选小”在交替。',
      code: `search(position, depth, red_turn):\n  if terminal: return win_or_loss_score(position)\n  if depth == 0: return evaluate(position)\n\n  best = red_turn ? -INF : +INF\n  for move in legal_moves:\n    captured = make(move)\n    score = search(position, depth - 1, !red_turn)\n    undo(move, captured)\n    best = red_turn ? max(best, score) : min(best, score)\n  return best`,
      steps: ['终止条件：胜负或到达搜索深度', '递归前 make，递归后 undo，并切换行棋方', '红方取 max，黑方取 min'],
      notes: '现在把刚才的树写成伪码。【按键】递归必须有停止条件：或者已经分出胜负，或者到了我们能承担的搜索深度。【按键】每展开一条边，先 make；子树返回后必须 undo，不能让上一个候选污染下一个。【按键】回传时，红方节点取大，黑方节点取小。这正是项目源码的写法。',
      sources: ['xiangqi_ai.cpp:1123','xiangqi_ai.cpp:1371','xiangqi_ai.cpp:1446'], takeaway: '棋树只是反复执行“试走—换方—悔棋”。'
    },
    {
      id: 's17', title: '被将时，多给它一点呼吸空间', eyebrow: '将军延伸', layout: 'cards',
      lead: '如果深度边界恰好落在强制应将前，就延长一层；但延伸预算必须有上限。',
      cards: [
        {title: '为什么延伸', text: '被将的一方选择受强制，直接静态评分很可能落在变化中间'},
        {title: '怎么限制', text: '初始给与深度相关的延伸预算，每用一次就减少'},
        {title: '能力边界', text: '有限延伸降低截断强制变化的风险；它仍受预算约束'}
      ],
      steps: ['深度到 0 但当前被将', '有预算时把有效深度加 1', '递归时减掉已用延伸预算'],
      notes: '递归的深度边界还有一个例外：当前一方被将。【按键】如果轮到一方应将，局面的可选着往往很受限。恰好在这里切断，容易让评分函数看到一个尚未完成的强制变化。【按键】项目在有延伸预算时，将当前有效深度加一。【按键】预算会在递归中消耗，因此延伸规模受控。它降低强制应将掉出搜索边界的风险，完整杀法仍由实际搜索深度决定。真实对局还有时间限制：固定深度没算完时，程序也必须有答案可交。',
      sources: ['xiangqi_ai.cpp:1127','xiangqi_ai.cpp:1148-1153','xiangqi_ai.cpp:1412-1441'], takeaway: '延伸把深度投向强制变化，也必须控制预算。'
    },
    {
      id: 's22', title: '固定搜八层，第八层没算完怎么办？', eyebrow: '现实约束 · 时间', layout: 'cards',
      lead: '时间可能在根节点只搜索完部分候选时到达；这一轮尚未形成完整比较。',
      cards: [
        {title: '固定目标', text: '一开始就搜深度 8，超时可能只搜完前几个根候选'},
        {title: '中断状态', text: '根节点仍有候选未搜索，本轮没有完成全部候选的同深度比较'},
        {title: '新目标', text: '任何时候被叫停，手里都有上一个完整深度的结果'}
      ],
      steps: ['深度 8 可能在根候选尚未全部比较时超时', '当前轮停止，保留上一轮全部完成的结果', '从浅到深逐轮完成，让任意中断点都有可返回答案'],
      notes: '假设一开始直接搜索八层。【按键】时间可能在这一轮中间到达，此时根节点只完成了前几个候选，后面的候选还没有得到同深度搜索。这一轮缺少完整比较。【按键】解决办法是先完整搜索一层并保存结果，再完整搜索两层、三层，逐轮加深。更深一轮中途停止时，直接返回上一轮已经完成的答案。这就是下一页的迭代加深。',
      sources: ['xiangqi_ai.cpp:1142-1147','xiangqi_ai.cpp:1545-1603'], takeaway: '搜索管理不只问能看多深，还要问超时时能返回什么。'
    },
    {
      id: 's23', title: '迭代加深：每爬完一层，先把答案收好', eyebrow: '按时交卷', layout: 'table',
      lead: '从深度 1、2、3……逐层完整搜索；当前层超时，返回最后完成的一层。',
      table: {headers:['深度','状态','最佳着','分数','处理'], rows:[
        ['1','已完成','M1','S1','保存'],
        ['2','已完成','M2','S2','覆盖为最后完整答案'],
        ['3','已完成','M3','S3','覆盖为最后完整答案'],
        ['4','超时','未完整','未完整','丢弃本轮，返回 M3']
      ]},
      steps: ['深度 1、2、3 每完成一轮，都保存完整答案', '深度 4 中途超时，本轮不作为最终答案', '引擎返回深度 3 的最后完整结果', '上一轮最佳着会帮助下一层先试更可能的好着'],
      notes: '【按键】我们先完整搜一层，得到一份很浅，但完整的答案。再搜两层，完成后覆盖它。【按键】三层也完成了，手里始终有一份根节点全部候选均被比较过的结果。【按键】四层搜到一半超时，就丢弃这个未完成轮，返回三层答案。【按键】表面看，前几层似乎重复计算。但浅层很便宜，而且上一轮找到的最佳着会帮助下一层更早建立 Alpha-Beta 边界；具体怎样保存这条经验，后面再讲。',
      sources: ['xiangqi_ai.cpp:1545-1587'], takeaway: '迭代加深同时提供可中断性和下一轮的排序经验。'
    },
    {
      id: 's24', title: '每隔一批节点检查时限', eyebrow: '时间控制 · 实际代码', layout: 'code',
      lead: '递归每 2048 个节点检查硬时限；完成一轮后，再判断是否还值得开始下一轮。',
      code: `if ((nodes & 2047) == 0):\n  if elapsed > time_limit:\n    stop_search = true\n\nfor depth = 1..63:\n  result = search(depth)\n  if stop_search: break\n  last_res = result\n  if elapsed > max_time * 0.16 && depth >= 4:\n    break`,
      steps: ['节点计数达到检查间隔时看表', '超时信号沿递归返回', '只在完成当前轮后更新 last_res', '一轮已花掉超过 16% 总预算时，不再启动增长更大的下一轮'],
      notes: '迭代加深还需要一个真正的停止信号。【按键】如果每个节点都调用时钟，查时间本身也有开销。这份代码每 2048 个节点检查一次硬时限。【按键】超时后，stop_search 会让递归层层退回。【按键】根搜索只有在整个深度完成后，才把结果存成 last_res。【按键】更深一轮的节点数通常会明显增长。如果刚完成的一轮已经用掉超过总预算的百分之十六，并且至少搜到深度四，代码就不再冒险启动下一轮；递归中的硬时限仍负责兜住实际超时。百分之十六是这个项目用于判断“下一轮大概率来不及完成”的经验阈值。',
      sources: ['xiangqi_ai.cpp:1142-1147','xiangqi_ai.cpp:1545-1603'], takeaway: '搜索过程持续检查时限，并始终保留最后一个完整结果。'
    },
    {
      id: 's07', title: '会递归以后，树立刻爆炸', eyebrow: '新问题 · 分支因子', layout: 'cards',
      lead: '候选数是 b，搜索深度是 d，朴素节点数大致随 b^d 增长。',
      cards: [
        {title: '多看一层', text: '不是多算一批节点，而是让现有的每个叶子再分叉'},
        {title: '叶子也未必平静', text: '稍后为了不停在吃子中间，深度边界外还可能继续展开'},
        {title: '纯教学算例', text: '假设每层平均 30 个候选：4 层约 81 万叶子，6 层约 7.29 亿叶子'},
        {title: '真正的问题', text: '我们是否必须知道每个候选的精确分？'}
      ],
      steps: ['一层变两层，每个叶子继续分叉', '教学假设 b=30：b⁴=810000，b⁶=729000000', '将问题改成：找最好着是否需要算完所有着？'],
      notes: '现在我们有一个逻辑上正确的朴素搜索了，但它很快就算不完。【按键】多看一层，并不是单纯多几个节点，而是每个叶子又长出一批孩子。【按键】用一个纯教学假设感受增长速度：如果每层平均三十个候选，四层约有八十一万个叶子，六层约有七亿两千九百万个。这里的三十不是本项目实测，只用来展示指数增长。【按键】稍后为了避免停在吃子中间，我们还会在少数叶子外继续搜索。【按键，停顿】如果最终目的只是选一手棋，我们需要知道每一条差路到底差多少吗？',
      sources: ['xiangqi_ai.cpp:1123'], takeaway: '搜索的瓶颈来自指数级分叉，不是单个节点的评分。'
    },
    {
      id: 's07a', title: '后面怎样加速？先看“不少算”的方法', eyebrow: '搜索加速路线图 · 1 / 2', layout: 'table',
      lead: '先用边界、叶子稳定、局面记忆和排序，让同样的搜索更早得到答案。',
      table: {headers:['方法','核心作用'], rows:[
        ['Alpha-Beta','边界已足够决定选择时，停止剩余分支'],
        ['QS','叶子只续搜战术候选；被将时生成全部应将'],
        ['SEE（QS 筛选）','未被将时过滤明显亏损的吃子'],
        ['Zobrist key','用可增量更新的短指纹标识局面'],
        ['TT lookup','用 key 快速定位已有搜索记录'],
        ['TT reuse','复用足够深的精确值或上下界'],
        ['TT replacement','固定容量下保留更值得复用的记录'],
        ['TT move','优先尝试缓存记录的最佳着'],
        ['吃子排序 + SEE','先试更可能有利的交换'],
        ['Killer','优先试同层曾造成截断的安静着'],
        ['Counter','优先试曾有效回应上一着的着法'],
        ['History','按安静着长期成功记录调整顺序']
      ]},
      steps: ['先减少为得到同一结论而展开的分支','再复用已算局面，并把可能的好着提前','SEE 在这里分别服务于 QS 筛选与吃子排序'],
      notes: '这两页先给后文一张地图，不展开公式。【按键】Alpha-Beta 在边界足够时停止；QS 只稳定普通深度边界的战术局面：未被将时主要扩展吃子，并用 SEE 过滤明显亏损的交换；被将时必须生成全部应将，而不是只搜吃子。这样避免把所有安静着一起向外扩展。【按键】Zobrist key 和置换表负责认出、定位、复用和替换已算记录。【按键】最后五项都不改变候选集合，只把更可能尽早建立边界的着法排到前面。吃子排序中的 SEE 只用于比较交换前景；后面还会看到 SEE 的第三种用途——浅层直接跳过候选。',
      sources: ['xiangqi_ai.cpp:863-1118','xiangqi_ai.cpp:1123-1540'], takeaway: '先少做无效展开，再让好着更早建立边界。'
    },
    {
      id: 's07b', title: '再往后：少搜、补搜，以及让查询更便宜', eyebrow: '搜索加速路线图 · 2 / 2', layout: 'table',
      lead: '后半程用便宜试探和选择性搜索集中预算，再用补搜与查表控制代价。',
      table: {headers:['方法','核心作用'], rows:[
        ['IID','没有领路着时，先浅搜找排序线索'],
        ['PVS','首着全窗，其余先用窄窗挑战'],
        ['Aspiration','围绕上一轮分数先搜较窄窗口'],
        ['LMR','较晚且不显眼的着先减深搜索'],
        ['LMP','浅层直接跳过过晚的安静着'],
        ['Futility','乐观估计仍不够时跳过浅层安静着'],
        ['SEE pruning','浅层跳过静态交换明显亏损的候选'],
        ['RFP','静态分明显越界时提前截断'],
        ['Razoring','浅层明显差势时转交 QS 复核'],
        ['NMP','用空着减深试探能否提前截断'],
        ['第二遍补搜','触发补漏条件后关闭三类局部跳过并重跑'],
        ['车炮攻击表','增量维护行列占位，直接查预计算结果']
      ]},
      steps: ['便宜试探先回答“是否值得完整搜索”','选择性方法把预算集中到更可能关键的分支','第二遍补搜降低局部漏棋风险，车炮查表降低重复查询成本'],
      notes: '再看后半张地图。【按键】IID、PVS 和 Aspiration 用较便宜的搜索先试探。LMR 只是暂时少搜层数；LMP、Futility 和 SEE pruning 会直接跳过候选，其中 SEE pruning 是 SEE 的第三种用途，与前页的 QS 筛选和吃子排序分开。【按键】RFP、Razoring 和 NMP 都尝试在完整展开以前取得足够证据。它们带来选择性风险，所以代码在特定异常结果下从候选表开头做第二遍，并关闭 LMP、Futility、SEE pruning 这三类局部跳过。【按键】最后，车炮攻击表不减少搜索节点，而是通过 make/undo 增量维护占位，让每次直线查询直接命中预计算结果。',
      sources: ['xiangqi_ai.cpp:1177-1540','xiangqi_ai.cpp:210-279','xiangqi_ai.cpp:485-604','xiangqi_ai.cpp:669-711'], takeaway: '少搜方法集中预算；补搜与查表分别控制漏棋和单次查询成本。'
    },
    {
      id: 's08', title: '先算清 A：对手会留给我们几分？', eyebrow: '第一次少算 · 建立参照', layout: 'tree',
      lead: '红方考虑候选 A；下一层轮到黑方在 3 和 5 中取小。',
      tree: {kind:'alphabeta', values:[3,5,2,null,null], stage:1, caption:'3 / 5 / 2 是教学分，不是真实棋局评分'},
      steps: ['A 的第一个黑方应手得分为 3', 'A 的第二个黑方应手得分为 5', '黑方取 min(3,5)=3，红方已有一条值为 3 的候选'],
      notes: '现在用一棵极小的教学树做一次选择。这里的 3、5、2 都是教学分。【按键】A 的第一个应手是 3，第二个应手是 5。这一层轮到对手选。【停顿】它会留下 3，还是 5？它会选对红方更不利的 3。【按键】所以 A 在这棵树中的回传值是 3。根节点已经拥有 A 这条三分路线，这会成为判断后续候选的门槛。',
      sources: ['xiangqi_ai.cpp:1451-1478'], takeaway: '先完整算清一条路，才有可以比较的边界。'
    },
    {
      id: 's09', title: 'B 还没算完，但也许已经够了', eyebrow: '第一次少算 · 请你判断', layout: 'tree',
      lead: 'B 的第一个对手应手是 2；后面也许还藏着 10。要继续吗？',
      tree: {kind:'alphabeta', values:[3,5,2,null,null], stage:2, caption:'已知 A=3；B 的 MIN 节点已看到 2'},
      steps: ['B 的第一个对手应手得分为 2', '后续应手仍是未知数', '关键问题：轮到谁挑 B 下面的应手？'],
      notes: '【按键】我们开始算 B，第一个对手应手是 2。【按键】后面还有两个问号。也许里面藏着 10，甚至 100。我们要继续吗？【停顿，等现场回答】也许后面更好，但这些应手是谁挑？对手已经有一个把我们压到 2 的方法，它会放着 2 不选，主动送我们 10 吗？【停顿】',
      sources: ['xiangqi_ai.cpp:1451-1508'], takeaway: '不知道后面的精确值，也可能已经有足够证据停止。'
    },
    {
      id: 's10', title: '我们不知道 B 是几分，但知道不会选它', eyebrow: '获得能力 · Alpha-Beta', layout: 'tree',
      lead: '红方已有 A=3；B 下面的黑方已有办法把红方压到 2。',
      tree: {kind:'alphabeta', values:[3,5,2,null,null], stage:3, caption:'问号分支不搜；B 只需知道上界已不足以挑战 A'},
      steps: ['B 剩余分支已不会改变根节点选择，因此不搜', 'B 的精确分数仍然未知', 'Alpha-Beta 用 alpha/beta 边界判断何时可以停止'],
      notes: '【按键】现在把 B 剩下的树枝变灰。我们还不知道 B 的精确分数。【按键】它可能最后是 2，也可能还有更低的黑方应手。但黑方已经能把 B 压到不高于 2，而红方已有 A=3，所以红方不会改选 B。【按键】Alpha-Beta 的核心就在这里：无需把 B 算到精确，也已有足够证据确定根节点的选择。alpha 和 beta 记录选择门槛，不代表某一方的局面分数。',
      sources: ['xiangqi_ai.cpp:1451-1508'], takeaway: '边界已足以做选择时，精确值可以不再计算。'
    },
    {
      id: 's10a', title: 'Alpha 和 Beta 是两道选择门槛', eyebrow: '从直觉到变量', layout: 'cards',
      lead: '沿用红方分数固定视角：MAX 祖先已有至少 alpha 的别路，MIN 祖先已有至多 beta 的别路。',
      cards: [
        {title: 'alpha：下门槛', text: '某个 MAX 祖先已有别的选择能拿到至少 alpha；更低的当前分支不会被它选中'},
        {title: 'beta：上门槛', text: '某个 MIN 祖先已有别的选择能把红方压到至多 beta；更高的当前分支不会被它放行'},
        {title: '值得求精确的区间', text: '当前分支只有落在 alpha 与 beta 之间，才可能改变祖先的选择'}
      ],
      steps: ['alpha 来自 MAX 已经拥有的替代选择', 'beta 来自 MIN 已经拥有的替代选择', '两者随递归传入，构成当前搜索窗口'],
      notes: '刚才那棵树里，A 等于 3，所以根节点这个 MAX 已经拥有一条至少得 3 的别路。这个门槛叫 alpha。【按键】beta 是对称的：某个 MIN 祖先如果已经有一条路能把红方压到至多 beta，它就不会选择一个让红方得分更高的分支。【按键】要注意，这两者来自祖先已经拥有的替代选择，不是随口断言当前局面的真实分数一定大于 alpha、小于 beta。当前分支只有可能落在两道门槛之间时，继续求精确值才可能改变祖先选择。',
      sources: ['xiangqi_ai.cpp:1123','xiangqi_ai.cpp:1451-1508'], takeaway: 'alpha 和 beta 记录祖先已有的选择门槛。'
    },
    {
      id: 's10b', title: '把刚才的 A / B 翻译成 alpha 和 beta', eyebrow: '同一棵树 · 对应变量', layout: 'tree',
      lead: 'A=3 让根节点得到 alpha=3；搜索 B 时，第一个黑方应手 2 把 beta 压到 2。',
      tree: {kind:'alphabeta', values:[3,5,2,null,null], stage:3, caption:'同一棵树：A=min(3,5)=3；B 的 MIN 节点先看到 2'},
      code: `alpha = 3              // 根节点 MAX 已有 A=3\nbeta = +INF            // 进入 B 的 MIN 节点\n\nscore = 2              // B 的第一个黑方应手\nbeta = min(beta, score) // beta 变为 2\n\nif alpha >= beta:      // 3 >= 2\n  break                // 停止 B 的剩余分支`,
      steps: ['A=min(3,5)=3，根节点把 alpha 提高到 3', 'B 的首个应手 2 令 beta=2；alpha≥beta，停止两个未知分支'],
      notes: '现在把刚才三页演示逐项对应到变量。【按键】A 的黑方节点在 3 和 5 中取小，回传 3；根节点是红方 MAX，于是它手里的下门槛 alpha 从负无穷提高到 3。【按键】接着搜索 B。B 下面轮到黑方 MIN，它继承 alpha=3，自己的 beta 从正无穷开始。【按键】第一个应手得到 2，beta 就从正无穷降到 2。此时 alpha=3 已经大于等于 beta=2。【按键】MIN 后面即使继续搜索，也只可能让 B 保持 2 或变得更低；B 已经无法超过 A=3，所以代码在这里停止剩余分支。',
      sources: ['xiangqi_ai.cpp:1123','xiangqi_ai.cpp:1451-1508'], takeaway: '窗口收紧到交叉时，当前分支已经失去影响祖先选择的机会。'
    },
    {
      id: 's12', title: '深度到了，交换却还没结束', eyebrow: '地平线效应 · 走前', layout: 'board',
      lead: '固定深度只规定“看到第几步”，不会等棋盘上的吃子与反吃自然结束。',
      boards: [{
        fen:'4k4/9/9/2n6/c8/R8/4P4/9/9/4K4 w', caption:'走前：红方走，红车可以吃掉前方黑炮',
        highlights:[{square:'a5',kind:'from'},{square:'a4',kind:'capture'},{square:'c3',kind:'warning'},{square:'b3',kind:'leg'}],
        arrows:[{from:'a5',to:'a4',kind:'capture'}], annotations:[{square:'a5',text:'红车'},{square:'a4',text:'黑炮'},{square:'c3',text:'黑马'}]
      }],
      steps: ['红车向前一格吃黑炮', '这一手恰好用完普通搜索深度', '黑马仍能经过空马腿 (3,1) 吃到同一目标格'],
      notes: '看这个局面：红车向前一格，可以吃掉黑炮。【按键】假设普通搜索的深度恰好在这一手用完，评分函数只看到红方刚得到一枚炮。【按键】固定深度不会等待交换自然结束。再看右上方的黑马：它通往红车所在格的马腿是空的，下一步还能把车吃回来。【停顿】此刻拿静态评分收尾，会漏掉什么？',
      sources: ['xiangqi_ai.cpp:1151-1153'], takeaway: '固定深度是人为切口，战术交换不会恰好在切口停止。'
    },
    {
      id: 's13', title: '第一帧：红车吃炮，如果现在停就会高估', eyebrow: '地平线 · 吃子之后', layout: 'compare',
      lead: '红车吃掉黑炮后，静态评分先记下“红方多吃一炮”；交换的下一步尚未进入叶子分数。',
      boards: [
        {fen:'4k4/9/9/2n6/c8/R8/4P4/9/9/4K4 w',caption:'走前',highlights:[{square:'a5',kind:'from'},{square:'a4',kind:'capture'}],arrows:[{from:'a5',to:'a4',kind:'capture'}],annotations:[]},
        {fen:'4k4/9/9/2n6/R8/9/4P4/9/9/4K4 b',caption:'走后：(5,0) 已空，(4,0) 为红车，黑炮消失',highlights:[{square:'a4',kind:'to'}],arrows:[],annotations:[]}
      ],
      steps: ['红车吃炮后，叶子局面暂时少了一枚黑炮', '静态评分会立刻反映这次得子', '黑方下一步能否反吃，决定这份收益能否保住'],
      notes: '左边是走前，右边是红车吃炮后的叶子局面。【按键】红方刚吃掉一枚黑炮，静态评分会立刻把这次得子记进去。【按键】可这份分数还没有回答一个关键问题：黑方下一步能不能把红车吃回来？固定深度恰好把未来反击挡在视野外，这就是地平线效应。',
      sources: ['xiangqi_ai.cpp:434','xiangqi_ai.cpp:1151-1153'], takeaway: '吃子后的瞬时高分，可能只是未完成交换的假象。'
    },
    {
      id: 's14', title: '第二帧：黑马吃回红车', eyebrow: '地平线 · 反吃', layout: 'compare',
      lead: '黑马经过空马腿跳到红车所在格：红车被吃，黑马留在目标格。',
      boards: [
        {fen:'4k4/9/9/2n6/R8/9/4P4/9/9/4K4 b',caption:'反吃前：黑方走',highlights:[{square:'c3',kind:'from'},{square:'b3',kind:'leg'},{square:'a4',kind:'capture'}],arrows:[{from:'c3',to:'a4',kind:'capture'}],annotations:[{square:'b3',text:'马腿为空'}]},
        {fen:'4k4/9/9/9/n8/9/4P4/9/9/4K4 w',caption:'反吃后：(3,2) 已空，(4,0) 为黑马，红车消失',highlights:[{square:'a4',kind:'to'}],arrows:[],annotations:[]}
      ],
      steps: ['马腿为空，黑马能够回吃', '黑马吃车后占据目标格，红车从棋盘消失', '按基础子力计算，红方得炮 450、失车 1000，净变化 −550'],
      notes: '【按键】现在轮到黑方。因为马腿为空，黑马可以跳到红车所在格完成回吃。【按键】反吃以后，红车从棋盘消失，黑马留在目标格。【按键】只按项目的基础子力价格计算，红方眼前得到一枚炮 450，随后失去一辆车 1000，净变化是 -550。当前 evaluate() 还会加入位置分，但基础子力账已经足以说明：在交换中间截断，会把暂时得炮误当成已经赚到。【停顿】最直接的修法似乎是把所有分支都多搜几层，它的代价是什么？',
      sources: ['xiangqi_ai.cpp:89-99','xiangqi_ai.cpp:669','xiangqi_ai.cpp:1030'], takeaway: '一串吃与反吃要看到相对稳定，才适合下静态结论。'
    },
    {
      id: 's14a', title: '为什么不把 Minimax 统一多搜几层？', eyebrow: '从全面加深到选择性加深', layout: 'compare',
      lead: '普通加深会让每个叶子展开全部合法候选；我们眼前只需要把尚未结束的激烈交换继续看下去。',
      cards: [
        {title: '整棵树多搜一层', text: '每个叶子都生成车马炮兵的全部合法着；大量平静走法也一起分叉'},
        {title: '整棵树多搜两层', text: '新长出的每个节点再次展开全部候选，节点数继续按分支因子成倍增长'},
        {title: '仍可能切在交换中', text: '统一增加固定层数，只把截断线向后推；另一条更长交换仍可能跨过新边界'},
        {title: '选择性继续', text: '普通深度用完后，只沿吃子、吃回等未平静变化多看几步'}
      ],
      steps: ['全面加深把平静走法和战术走法一起展开', '固定增加层数仍可能停在更长交换中', '把额外计算集中到未结束交换，分支通常更少'],
      notes: '最直接的想法是：既然少看一步会错，那就让普通 minimax 统一多搜几层。【按键】问题是普通搜索在每个叶子都会生成全部合法候选。大量与眼前交换无关的平静走法也一起分叉，多一层就让所有叶子再长一批孩子，多两层还会继续相乘。【按键】而且固定多搜两层只是把截断线向后推。遇到更长的吃子链，新的边界仍可能落在交换中间。【按键】我们真正需要的是把额外计算集中到仍在剧烈变化的局部：普通深度用完后，优先沿吃子和吃回继续几步。这样的候选通常比全部合法着少，能以较低成本把眼前交换看得更完整；具体局面仍可能产生很多吃子，因此它不保证每次都便宜。',
      sources: ['xiangqi_ai.cpp:669','xiangqi_ai.cpp:1030-1119'], takeaway: '额外深度应优先花在尚未结束的强制变化上。'
    },
    {
      id: 's15', title: '普通深度归零，QS 接住这个叶子', eyebrow: 'Quiescence Search · 入口', layout: 'board',
      lead: '红车吃炮用完普通深度后，程序进入 QS；此时轮到黑方，交换仍能继续。',
      boards: [{fen:'4k4/9/9/2n6/R8/9/4P4/9/9/4K4 b',caption:'普通 depth=0 · 黑方行棋',highlights:[{square:'c3',kind:'from'},{square:'a4',kind:'capture'}],arrows:[{from:'c3',to:'a4',kind:'capture'}],annotations:[{square:'a4',text:'红车刚吃炮'},{square:'c3',text:'黑马还能回吃'}]}],
      code: `if (depth <= 0) {\n  return qs(alpha, beta, maximizingPlayer, 0);\n}`,
      steps: ['普通搜索停在红车刚吃炮的局面', 'QS 从 qsDepth=0 开始，沿黑马回吃继续看'],
      notes: '普通搜索已经走到红车吃炮，depth 用完了。【按键】这里把同一个局面、同一组 alpha 和 beta，以及当前轮到哪一方，交给 qs；qs 就是静止搜索函数。最后一个参数从零开始，单独记录 QS 又向前走了几步。【按键】当前轮到黑方，黑马回吃红车是一手吃子，所以这段尚未结束的交换能够继续进入搜索。',
      sources: ['xiangqi_ai.cpp:1148-1153'], takeaway: 'QS 是普通搜索到达叶子后的另一段递归搜索。'
    },
    {
      id: 's15b', title: '每次进入 QS，先决定候选与停止条件', eyebrow: 'Quiescence Search · 入口判断', layout: 'table',
      lead: '未被将时先用 stand-pat 收紧窗口；被将时必须寻找应将；qsDepth 限制额外搜索。',
      table: {headers:['当前状态','QS 的处理'],rows:[['未被将','先计算 stand-pat；窗口未截断时，准备吃子候选'],['被将，qsDepth 0–3','跳过 stand-pat，准备全部走法，由下一页过滤出合法应将'],['被将，qsDepth 4–6','只确认有无合法应将：有则 evaluate，无则判负'],['qsDepth > 6','直接 evaluate，结束 QS']]},
      code: `qs(alpha, beta, maximizing, qsDepth):\n  inCheck = is_in_check(maximizing)\n  if !inCheck:\n    standPat = evaluate()\n    if maximizing:\n      if standPat >= beta: return beta\n      alpha = max(alpha, standPat)\n    else:\n      if standPat <= alpha: return alpha\n      beta = min(beta, standPat)\n\n  if qsDepth > 6: return evaluate()\n  if inCheck and qsDepth > 3:\n    if 存在合法应将: return evaluate()\n    return maximizing ? -30000 + qsDepth\n                      :  30000 - qsDepth\n\n  moves = inCheck ? 全部走法 : 吃子候选`,
      notes: '每次调用 qs，都从这组入口判断开始。【按键】当前没有被将时，先计算 stand-pat，以当前局面的静态分作为窗口基准；它是一次评分，不是棋规中的停着或让一拍。MAX 用 max 明确更新 alpha，MIN 用 min 明确更新 beta；越过对侧门槛就返回。【按键】当前正在被将时，停在原地不合法，所以跳过 stand-pat。qsDepth 从零到三时先生成全部走法，再由下一页的试走检查留下合法应将。【按键】项目还设置成本上限：qsDepth 超过六直接 evaluate；被将且深度在四到六时逐一试走候选，只确认是否存在合法应将，有则 evaluate，无则判负。准备好 moves 以后，才进入下一页的循环。',
      sources: ['xiangqi_ai.cpp:1030-1090'], takeaway: '入口判断先给出基准分、候选集合和深度边界，再把候选交给递归循环。'
    },
    {
      id: 's15a', title: '候选准备好后：走一步，再调用 QS 自己', eyebrow: 'Quiescence Search · 递归循环', layout: 'code',
      lead: '这是 qs 的后半段：试走、过滤非法着、同名递归、撤销，再更新当前节点的窗口。',
      code: `hasLegal = false\nfor m in moves:\n  captured = make(m)\n  if is_in_check(maximizing):\n    undo(m, captured); continue\n  hasLegal = true\n\n  score = qs(alpha, beta, !maximizing, qsDepth + 1)\n  undo(m, captured)\n\n  if maximizing:\n    if score >= beta: return beta\n    alpha = max(alpha, score)\n  else:\n    if score <= alpha: return alpha\n    beta = min(beta, score)\n\nif inCheck and !hasLegal:\n  return maximizing ? -30000 + qsDepth : 30000 - qsDepth\nreturn maximizing ? alpha : beta`,
      steps: ['合法着调用同一个 qs：换行棋方，qsDepth 加 1', '子节点返回后 undo，再更新 alpha 或 beta', '被将且没有合法应将时，返回当前行棋方的败分'],
      notes: '这段紧接上一页准备好的 moves。【按键】试走 m 后，先检查刚走棋的一方是否仍被将；非法就撤销并跳过，只有合法着才把 hasLegal 设为 true。【按键】随后 qs 再次调用 qs 自己：行棋方取反，qsDepth 加一，窗口传入下一层。每次进入下一层，又会从上一页的入口重新判断新局面是否被将；吃子若形成将军，下一层就准备全部应将。【按键】子节点返回后先 undo，再按 MAX 或 MIN 更新窗口。循环结束时，如果当前本来被将却一手合法应将也没有，就按当前行棋方判负；未被将且没有吃子候选时，则返回 stand-pat 已经收紧后的 alpha 或 beta。刚才的实例因此会真正走出黑马吃车。',
      sources: ['xiangqi_ai.cpp:1091-1119'], takeaway: '同名递归展开吃与反吃；hasLegal 补上被将无应手的终局出口。'
    },
    {
      id: 's16', title: '比 QS 更快、更粗糙的 SEE', eyebrow: '静态交换评估 · SEE', layout: 'compare',
      lead: 'SEE 只估算同一目标格上的连续交换；它比递归搜索便宜，也更粗糙，被 QS 筛选、主搜索排序和浅层剪枝共同调用。',
      boards: [
        {
          fen: '4k4/9/9/2n6/c8/R8/4P4/9/9/4K4 w',
          caption: '同样车 900 吃炮 400 · 有黑马回吃 · SEE = −500',
          orientation: 'red',
          highlights: [{square:'a5',kind:'from'},{square:'a4',kind:'capture'},{square:'c3',kind:'focus'}],
          arrows: [{from:'a5',to:'a4',kind:'capture'}],
          annotations: [{square:'c3',text:'黑马可回吃'}]
        },
        {
          fen: '4k4/9/9/9/c8/R8/4P4/9/9/4K4 w',
          caption: '同样车 900 吃炮 400 · 无黑马回吃 · SEE = +400',
          orientation: 'red',
          highlights: [{square:'a5',kind:'from'},{square:'a4',kind:'capture'}],
          arrows: [{from:'a5',to:'a4',kind:'capture'}],
          annotations: [{square:'c3',text:'移走回吃者'}]
        }
      ],
      code: `SEE(move):
  固定首个吃子的目标格
  双方轮流选最低价值攻击子吃回
  从交换链末端倒推净收益

不生成目标格之外的完整应手树`,
      steps: ['SEE 固定在一个目标格上估算双方连续吃回，不展开完整棋树', '它比 QS 递归便宜，但看不到目标格之外的全局战术', '两盘都是红车吃黑炮，进攻子和受害子面值完全相同', '仅仅有无黑马回吃，就让结果从 +400 变成 −500'],
      notes: 'SEE，也就是 Static Exchange Evaluation，静态交换评估。它不是 QS 完成后的下一段搜索，而是一个更便宜、更粗糙的局部估算：固定一个目标格，假设双方围绕这个格子连续吃回，再算发起交换的一方最终净赚还是净亏。它不展开完整棋树，也看不到目标格之外的弃子引将、腾线或做杀。\n\n[按键] 源码在三个位置调用 SEE。非将军的 QS 准备吃子候选时，便宜子吃贵子直接保留；贵子吃便宜子才用 SEE 过滤明显亏损的交换。主搜索还用 SEE 调整吃子排序，并在受保护的浅层条件下用它剪枝。因此 SEE 是多个搜索环节调用的局部工具，不是排在 QS 后面的独立阶段。\n\n[按键] 左右两盘的候选完全相同，都是价值九百的红车吃价值四百的黑炮。右盘没有回吃者，这笔交换停在吃炮，SEE 是正四百；左盘只多了一匹能攻击目标格的黑马，车吃炮后马再吃车，SEE 变成负五百。进攻子和受害子面值没有变化，结论却相反，所以两个面值只能决定“要不要进一步检查”，不能判断交换最终是否划算。',
      sources: ['象棋教学局面核验.md:B','xiangqi_ai.cpp:874-1027','xiangqi_ai.cpp:1071-1082'],
      takeaway: 'SEE 是搜索内部复用的局部交换估算：更快、更粗糙，不等于一段完整搜索。'
    },
    {
      id: 's16a', title: '目标格上的交换，怎样变成一串数字？', eyebrow: 'SEE · 轮流取最低价值攻击子', layout: 'code',
      lead: '源码使用独立的 SEE 价值表：车 900，马和炮 400；它不读取 PST，也不同于前面的教学价格。',
      code: `gain[0] = see_value(victim);       // 先记吃到的子
on_sq = see_value(attacker);         // 目标格上现在是谁
side = 对方;

while ((an = attackers_to(target, side, occupancy)) > 0) {
  best = 价值最低的攻击子;
  gain[n] = on_sq - gain[n - 1];
  on_sq = see_value(best.piece);
  从占位中移除 best 的起点;        // 后方车炮可能因此显露
  side = !side;
}`,
      table: {
        headers: ['时刻', '本轮最低价值攻击子', 'gain 计算', '得到'],
        rows: [
          ['红车吃黑炮', '红车 900', 'gain[0] = 黑炮价值', '400'],
          ['黑马回吃红车', '黑马 400', 'gain[1] = 目标格红车 900 − gain[0] 400', '500'],
          ['没有后续攻击子', '交换链结束', '进入从后向前回推', '待定']
        ]
      },
      steps: ['victim 是首着被吃子；gain[0] 先记它的 SEE 价值', 'on_sq 是当前站在目标格上的棋子价值', 'attackers_to 找当前一方所有攻击者，再选价值最低者', '每移除一个攻击者起点，都同步改变行列占位，重新发现后方车炮攻击', '本例得到原始序列 gain = [400, 500]'],
      notes: '先把价值表分清：SEE 自己使用一张简化交换表，将 10000、车 900、马和炮 400、士和相 120、兵 100。它服务于交换次序，不读取 PST，也不能拿前面讲解评价函数时的价格代入。【按键】victim 是第一手被吃的黑炮，所以 gain[0]=400；attacker 是吃上来的红车，on_sq=900。接着轮到黑方，attackers_to 找出能攻击 (4,0) 的黑子，源码从中选择价值最低的攻击子，这里是价值 400 的黑马。于是 gain[1]=900−400=500。每选出一枚攻击子，程序把它的起点从临时棋盘和行列占位中移除，再重新找攻击者；如果它原本挡住后方车或炮，这一步就会显露新的远程攻击。这里没有第三枚攻击子，原始交换序列停在 [400,500]。但 400 和 500 还不能直接当作首着收益，因为轮到任何一方时，它都可以选择停止交换。',
      sources: ['xiangqi_ai.cpp:874-1008'],
      takeaway: '前向循环生成交换账：最低价值攻击子依次加入，移除占位后重新发现攻击线。'
    },
    {
      id: 's16b', title: '双方都可以停手：从交换链末端倒推', eyebrow: 'SEE · 回推净收益与实际用途', layout: 'code',
      lead: '后续交换对当前一方不利时，它会停手；返回值表示发起首个吃子的一方最终净赚或净亏。',
      code: `// 本例前向结果：gain = [400, 500]
gain[0] = -max(-gain[0], gain[1]);
        = -max(-400, 500);
        = -500;

return gain[0];  // 红车吃炮的 SEE 净收益`,
      table: {
        headers: ['使用位置', '触发条件', '对 SEE = −500 的动作', '强度与目的'],
        rows: [
          ['QS 叶子筛选', '未被将；贵子吃便宜子；阈值 0', '不收入 QS 候选', '过滤：不进入 QS 递归'],
          ['主搜索吃子排序', '贵子吃便宜子；阈值 0', '放入较低排序档', '排序：仍然会搜索'],
          ['浅层主搜索剪枝', '非根、未被将、深度 ≤ 4；阈值 −50', '第一遍跳过', '剪枝：特定失败时第二遍恢复']
        ]
      },
      steps: ['gain[1]=500 表示黑马回吃对黑方有利，黑方会选择继续', '从末端应用源码回推式，首着结果变成 −500', 'SEE 始终采用首个吃子方视角；负数表示发起方净亏', '同一个 SEE 值在三处承担不同强度的动作'],
      notes: '现在从最后一步向前问：“轮到这一方时，继续交换和停手，哪个更好？”源码用 `gain[d-1] = -max(-gain[d-1], gain[d])` 把这个选择逐层折回。【按键】本例只有两层：黑马回吃能得到 500 的后续收益，所以黑方会继续；回到红车吃炮这一层，gain[0] 变成 −500。SEE 的返回值始终站在发起首个吃子的那一方：这里首着由红方发起，所以 −500 表示红方净亏 500 个 SEE 单位。\n\n[按键] 同一个数在三处承担不同强度的动作。QS 用零作门槛过滤候选，让明显亏损的贵子吃便宜子不进入叶子递归；过滤完成后，QS 自己的排序只比较被吃子价值，SEE 不参与这一步排序。主搜索排序只把负 SEE 吃子降档，仍会搜索。浅层主搜索在更严格条件下才用负五十作门槛，第一遍直接跳过；后面还有第二遍保护。SEE 只看同一目标格的交换，不看弃子引将、腾线和做杀等全局补偿。',
      sources: ['xiangqi_ai.cpp:1009-1027','xiangqi_ai.cpp:1071-1090','xiangqi_ai.cpp:1277-1284','xiangqi_ai.cpp:1362-1370'],
      takeaway: 'SEE 返回首着一方在目标格交换链上的净收益，供筛选、排序和浅层剪枝使用。'
    },
    {
      id: 'm08', title: '两条走棋顺序，汇到同一局面', eyebrow: '搜索遇到的重复劳动', layout: 'compare',
      lead: '两条路径都从初始局面出发；左右马的次序可以交换，四步后盘面和行棋方一致。',
      boards: [
        {fen:MEMORY_FOUR_HORSES,caption:'路径甲终点 · 红方行棋',highlights:[{square:'c2',kind:'to'},{square:'g2',kind:'to'},{square:'c7',kind:'to'},{square:'g7',kind:'to'}]},
        {fen:MEMORY_FOUR_HORSES,caption:'路径乙终点 · 红方行棋',highlights:[{square:'c2',kind:'to'},{square:'g2',kind:'to'},{square:'c7',kind:'to'},{square:'g7',kind:'to'}]}
      ],
      cards: [
        {title:'路径甲',text:'马八进七 → 马2进3 → 马二进三 → 马8进7'},
        {title:'路径乙',text:'马二进三 → 马8进7 → 马八进七 → 马2进3'},
        {title:'汇合',text:'同样的四匹马位置，同样轮到红方'}
      ],
      steps: ['路径甲先走画面左侧的马', '路径乙先走画面右侧的马', '终点状态完全相同，后续子树也完全相同'],
      notes: '我们刚刚已经看到，树的规模会迅速增长。现在看一种隐藏的重复劳动。路径甲先走左马，再走右马；路径乙把左右次序交换，黑方也做相同交换。【按键】走完以后，四匹马的位置相同，双方各走两步，仍轮到红方。从这个节点往下，引擎面对的是同一棵子树。如果第一条路已经算过，第二条路就应该复用结果。做到这一点，先要给局面一枚可快速维护的 key。',
      sources: ['xiangqi_ai.cpp:201','xiangqi_ai.cpp:444'], takeaway: '不同着序汇合时，缓存可以省掉整棵重复子树。'
    },
    {
      id: 'm02', title: '每个节点都重新扫描 90 格，能省掉吗？', eyebrow: '局面身份 · 更新成本', layout: 'compare',
      lead: '逐格比较能认出相同局面，但每个节点都重看整盘会反复累积成本。',
      boards: [{fen:MEMORY_START,caption:'当前局面 · 红方行棋',annotations:[{square:'a0',text:'从这里'},{square:'i9',text:'比到这里'}]}],
      cards: [{title:'身份内容',text:'90 个交叉点上的棋子 + 行棋方'},{title:'朴素比较',text:'每次最多检查 90 格'},{title:'我们想要',text:'走一步时，只处理真正变化的格子'}],
      steps: ['朴素办法：逐格记录与比较', '一着棋通常只改变少数事件', '目标：为完整局面维护一枚短指纹'],
      notes: '最直接的身份是九十个棋盘字符加行棋方。遇到节点时逐格生成、逐格比较，逻辑上能工作。【按键】但缓存查询会发生在大量节点上，每次都重新扫九十格，累积起来会很贵。一手马八进七真正改变的只是起点、终点和行棋方。我们需要一枚能随走子增量更新的短指纹。',
      sources: ['xiangqi_ai.cpp:444'], takeaway: '缓存 key 要既代表完整状态，又能随走子快速更新。'
    },
    {
      id: 'm03', title: '“哪枚棋子站在哪格”各有一枚随机指纹', eyebrow: 'Zobrist 哈希 · 构造', layout: 'cards',
      lead: '为每种“棋子—位置”组合准备一个 64 位随机数，再把当前发生的事件合起来。',
      cards: [{title:'棋子 × 位置',text:'Z[红车][(9,0)]、Z[红马][(9,1)]……彼此独立'},{title:'整盘指纹',text:'H（代码中的 current_hash）是所有当前事件随机数的 XOR'},{title:'行棋方',text:'轮到黑方时，再 XOR 一枚 TURN 指纹'}],
      steps: ['每个棋子—格位组合都有独立随机数', '当前所有棋子事件通过 XOR 合成一个结果', '轮到黑方时，再合入 TURN 指纹'],
      notes: '我们给每一个“棋子—格位”组合发一张随机号码。用 Z[棋子][格位] 表示：红车站 (9,0) 有一枚，站 (9,1) 又是另一枚。代码在启动时用固定种子生成这些 64 位随机数。【按键】当前盘上所有棋子号码通过 XOR，也就是按位异或，合成整盘指纹 H，代码中叫 current_hash。完整状态还包括行棋方；轮到黑方时，再异或 TURN 指纹。',
      sources: ['xiangqi_ai.cpp:201','xiangqi_ai.cpp:444'], takeaway: 'Zobrist key 由棋子格位与行棋方共同组成。'
    },
    {
      id: 'm04', title: '同一枚指纹拨两次，就回到原样', eyebrow: 'Zobrist 哈希 · XOR', layout: 'code',
      lead: 'XOR 像开关：第一次加入，第二次消去；合入次序不影响最后结果。',
      code: `H ^= X;   // 打开事件 X\nH ^= X;   // 再拨一次，X 被消去\n\nA ^ B ^ C == C ^ A ^ B`,
      steps: ['X ^ X = 0：同一事件拨两次会抵消', 'A ^ B ^ C = C ^ A ^ B：合入次序不影响结果', '撤销时重做同样的 XOR，即可恢复旧指纹'],
      notes: 'XOR 有两个很适合走子的性质。第一，同一个数异或两次会抵消。把“红马在 (9,1)”从指纹里拨掉，只要再异或一次对应随机数；撤销时再拨回来。【按键】第二，异或先后次序不影响结果。只要最后盘面和行棋方相同，合出的指纹就相同。下面把一着棋拆成几个开关。',
      sources: ['xiangqi_ai.cpp:500','xiangqi_ai.cpp:567'], takeaway: 'XOR 让加入、移除和撤销都使用同一种操作。'
    },
    {
      id: 'm05', title: '马八进七：只更新旧位置、新位置与行棋方', eyebrow: 'Zobrist 哈希 · 普通走子', layout: 'board',
      lead: '不吃子的普通走法用固定三次 XOR，无需重新扫描棋盘。',
      boards: [
        {fen:MEMORY_START,caption:'走前 · 红方行棋',highlights:[{square:'b9',kind:'from'},{square:'c7',kind:'to'}],arrows:[{from:'b9',to:'c7'}],annotations:[{square:'b9',text:'红马旧位置'}]},
        {fen:MEMORY_RED_HORSE,caption:'走后 · 黑方行棋',highlights:[{square:'b9',kind:'from'},{square:'c7',kind:'to'}],annotations:[{square:'c7',text:'红马新位置'}]}
      ],
      steps: ['H ^= Z[红马][(9,1)]　移除旧位置', 'H ^= Z[红马][(7,2)]　加入新位置', 'H ^= Z_TURN　红走变为黑走'],
      notes: '红方马八进七，内部坐标是 (9,1) 到 (7,2)。H 是整盘 current_hash，Z[棋子][格位] 是棋子站在该格的随机指纹。【按键】第一步，异或“红马在 (9,1)”，关掉旧事件。第二步，异或“红马在 (7,2)”，打开新事件。第三步，异或 TURN，把红方行棋切为黑方行棋。棋盘上无论有多少枚子，这一步都只需固定三次 XOR。',
      sources: ['xiangqi_ai.cpp:485','xiangqi_ai.cpp:500'], takeaway: '普通走子把全盘重算降为固定三次 XOR。'
    },
    {
      id: 'm06', title: '兵五进一吃卒：再移除目标格原来的卒', eyebrow: 'Zobrist 哈希 · 吃子', layout: 'board',
      lead: '吃子改变四件事：起点走子、目标格被吃子、终点走子、行棋方。',
      boards: [
        {fen:MEMORY_CAPTURE_BEFORE,caption:'走前 · 红方行棋',highlights:[{square:'e5',kind:'from'},{square:'e4',kind:'capture'}],arrows:[{from:'e5',to:'e4'}],annotations:[{square:'e4',text:'黑卒'}]},
        {fen:MEMORY_CAPTURE_AFTER,caption:'走后 · 黑方行棋',highlights:[{square:'e5',kind:'from'},{square:'e4',kind:'to'}],annotations:[{square:'e4',text:'红兵占据'}]}
      ],
      steps: ['H ^= Z[红兵][(5,4)]；H ^= Z[黑卒][(4,4)]', 'H ^= Z[红兵][(4,4)]', 'H ^= Z_TURN'],
      notes: '吃子比普通走法多一个开关。红兵从 (5,4) 走到 (4,4)，就是兵五进一，吃掉前面的黑卒。【按键】先关掉“红兵在 (5,4)”，再关掉“黑卒在 (4,4)”，然后打开“红兵在 (4,4)”，最后换行棋方。撤销时把这四次 XOR 再执行一次，就能恢复旧哈希。',
      sources: ['xiangqi_ai.cpp:500','xiangqi_ai.cpp:552'], takeaway: '吃子也只更新真正改变的事件。'
    },
    {
      id: 'm09', title: '现在，每个搜索节点都有一枚可快速更新的 key', eyebrow: 'Zobrist 哈希 · 接入缓存', layout: 'cards',
      lead: 'current_hash 用 64 位摘要完整局面，make/undo 只更新变化的事件。',
      cards: [
        {title:'完整状态',text:'棋子—格位事件与行棋方共同决定 current_hash'},
        {title:'增量维护',text:'make/undo 用同样的 XOR 开关更新和恢复指纹'},
        {title:'下一问',text:'用 key 找到旧记录后，怎样判断这份搜索证据能否复用？'}
      ],
      steps: ['current_hash 摘要棋子位置与行棋方', '走子和撤销都只更新变化的事件', '下一页把 key 映射到固定容量的置换表'],
      notes: '到这里，每个节点都有一枚便宜的局面 key：current_hash。它同时摘要棋子位置和行棋方，每次 make 或 undo 只对真正变化的事件做 XOR。【按键】现在把这枚 key 接入固定大小的置换表：先用它找到数组槽位，再判断槽里的旧搜索证据能不能复用。',
      sources: ['xiangqi_ai.cpp:198','xiangqi_ai.cpp:444','xiangqi_ai.cpp:500','xiangqi_ai.cpp:567'], takeaway: 'Zobrist key 解决节点身份与增量更新，置换表负责存放搜索证据。'
    },
    {
      id: 's18', title: '用局面 key 找到一个固定缓存槽位', eyebrow: '置换表 TT · 数组定位', layout: 'code',
      lead: '不同路径可能到达同一局面，后续搜索也会重复；置换表保存搜过的结果，供再次遇到时复用。',
      code: `TT_SIZE = 1 << 23          // 2^23 个槽位\nTT_MASK = TT_SIZE - 1      // 低 23 位全为 1\nindex = current_hash & TT_MASK\nentry = transposition_table[index]`,
      cards: [
        {title: '为什么是数组', text: '每个搜索节点都要查询；直接按下标访问，成本固定'},
        {title: '为什么用掩码', text: '容量是 2 的幂，hash & (SIZE−1) 直接取得低 23 位'},
        {title: '数组里放什么', text: '一个槽位保存一条局面搜索记录，稍后再逐字段展开'}
      ],
      steps: ['相同局面的子树无需从头再搜', 'TT_SIZE=2^23，所以合法下标是 0 到 2^23−1', 'TT_MASK=2^23−1，只保留 hash 的低 23 位', 'current_hash & TT_MASK 选中一个缓存槽位'],
      notes: '不同走子顺序可能汇聚到同一个局面。如果第一次已经把它后面的变化搜过，第二次从头搜索就是重复劳动。【按键】置换表把搜索结果存起来；Zobrist 的 64 位局面指纹负责让我们再次找到它。【按键】置换表是一段固定大小的数组，共二的二十三次方个槽位，下标从零到二的二十三次方减一。【按键】因为容量恰好是二的幂，掩码的低二十三位全是一。当前 hash 和它做按位与，就留下低二十三位，直接得到数组下标。【按键】这个过程很快，但从 64 位压到 23 位，许多不同 hash 必然会指向同一个槽位。',
      sources: ['xiangqi_ai.cpp:34-41','xiangqi_ai.cpp:1156'], takeaway: '掩码把 64 位局面指纹映射到固定大小的数组。'
    },
    {
      id: 's18c', title: '一条缓存记录，要说明证据怎样得到', eyebrow: 'TT · 字段与替换', layout: 'table',
      lead: '下标只负责定位槽位；读取前先核对完整 hash，再判断这份搜索证据能否复用。',
      table: {headers:['字段','回答的问题'], rows:[
        ['hash','槽内记录是否属于当前 64 位局面指纹？'],
        ['depth','当时从这个节点继续搜了多深？'],
        ['score + flag','分数是精确值，还是上界/下界？'],
        ['best_move','上次哪手最值得先搜？'],
        ['age','记录属于哪一轮根搜索年龄？']
      ]},
      cards: [
        {title: '写入同一槽位', text: '空槽、同一 hash、旧 age，或新记录深度不浅于旧记录时可替换'},
        {title: '每次开始思考', text: '根搜索开始时 tt_age 加一，让旧轮次记录可被优先淘汰'}
      ],
      steps: ['hash 确认身份，depth 与 flag 说明分数证据', 'best_move 即使不能复用分数，也可用于排序', 'age 和 depth 参与固定容量下的替换'],
      notes: '下标只负责定位槽位；读取记录前，还要确认槽内保存的完整 hash 等于 current_hash。确认身份以后，还要知道这条证据有多强。【按键】depth 说明当时从这里继续搜了多深；score 和 flag 合起来说明它是精确值，还是只证明了一个方向的界；best move 记录上次最值得先试的走法。【按键】age 是根搜索的年龄。每次开始一次新的思考，年龄加一。【按键】写入同一槽位时，空记录、同一 hash、旧年龄，或新搜索至少同样深，都允许替换。这样固定容量会更多保留较新、较深的证据。',
      sources: ['xiangqi_ai.cpp:80-87','xiangqi_ai.cpp:1521-1549'], takeaway: 'TT 条目保存搜索证据，也保存判断证据强弱所需的元数据。'
    },
    {
      id: 's19', title: '缓存存的是一个答案，还是一个范围？', eyebrow: 'TT · EXACT / ALPHA / BETA', layout: 'compare',
      lead: '先保存搜索开始时的原始窗口；深度足够且缓存界越过相应门槛时，才能直接停止。',
      cards: [
        {title: 'TT_EXACT', text: '例如原窗口 [3,8]，完整得到 5：当前搜索可直接返回 5'},
        {title: 'TT_ALPHA：上界', text: '记录值 2，且 2≤当前 alpha=3：当前分支够不到 MAX 已有门槛，可停止'},
        {title: 'TT_BETA：下界', text: '记录值 9，且 9≥当前 beta=8：MIN 已有更低的别路，不会放行，可停止'},
        {title: '深度不足', text: '不直接拿浅层分数代替深搜，但可先试表中 best_move'}
      ],
      steps: ['精确值可直接返回', '上界只有不高于当前 alpha 时足以停止', '下界只有不低于当前 beta 时足以停止', '深度不足或界未越门槛时，best_move 仍可用于排序'],
      notes: 'TT 里保存的分数要回到当前窗口中解释。【按键】同一 hash、记录深度足够时，精确值可以直接返回。【按键】如果记录的是上界二，而当前 alpha 是三，它已经证明当前路够不到 MAX 祖先已有的三分门槛，可以停止。【按键】如果记录的是下界九，而当前 beta 是八，它已经证明分数至少为九，MIN 祖先已有至多八分的替代选择，不会放行当前路，也可以停止。【按键】上界高于 alpha、下界低于 beta 时，证据还没有跨过对应门槛，仍需搜索。深度不足时也不能拿浅层分数代替深搜，但 best move 仍可用于排序。',
      sources: ['xiangqi_ai.cpp:1156-1170','xiangqi_ai.cpp:1521-1540'], takeaway: '界只能按界的方式使用；浅层最佳着仍可为深层带路。'
    },
    {
      id: 's20', title: '局面指纹还能帮我们在历史中找重复', eyebrow: '指纹的第二个用途', layout: 'cards',
      lead: '沿搜索路径保存每步的指纹，就能快速发现当前状态是否曾在这条路上出现。',
      cards: [
        {title: '当前身份', text: 'current_hash 表示当前棋子摆法与行棋方'},
        {title: '路径记录', text: '每走一步，把新局面指纹保存在历史中'},
        {title: '发现重复', text: '当前指纹与早先记录相同，说明这条路又来到同一状态'}
      ],
      steps: ['make 之后把新局面指纹记入当前路径', '搜索节点用当前指纹查找早先相同状态', '指纹负责快速定位；具体裁决还要读到达过程'],
      notes: '局面指纹还有第二个用途。每次 make 之后，项目把新局面的 current_hash 记入当前搜索路径。【按键】如果当前指纹与早先某个记录相同，就快速定位到“这条路又来到了同一状态”。这和置换表的分工不同：置换表复用子树搜索证据，路径记录保存局面如何到达。具体裁决还要结合循环中每一步是否将军。',
      sources: ['xiangqi_ai.cpp:302-306','xiangqi_ai.cpp:633-660','xiangqi_ai.cpp:1129-1159'], takeaway: '同一枚局面指纹，既能定位缓存，也能帮助在当前路径中发现重复。'
    },
    {
      id: 's21', title: '安静着都不吃子，先搜谁？', eyebrow: '走法排序 · 基线问题', layout: 'tree',
      lead: '安静着是非吃子着；它们没有“吃了多贵的子”这个现成顺序。',
      tree: {kind:'ordering', before:['A 铺垫','B 防守','C 调整','D 触发截断'], after:['D 先搜','边界立即收紧','A / B / C 可更早停止'], stage:1},
      cards: [
        {title:'候选都合法',text:'排序不删走法，只改变递归尝试顺序。'},
        {title:'能截断的着在最后',text:'前面三棵子树先被展开，Alpha-Beta 很晚才拿到强边界。'},
        {title:'能截断的着在最前',text:'同一棵搜索树更早证明其余候选不必继续。'}
      ],
      steps: ['本项目把非吃子着称为安静着', '安静着没有被吃子价值可直接比较', '若能触发搜索截断的 D 排在最后，A/B/C 的子树已经付费', '把 D 提前不改变 Minimax 结果，只让 Alpha-Beta 更早发挥'],
      notes: '吃子着至少可以先看被吃子价值和 SEE，安静着没有这个现成信号。这里的安静着，就是本项目中所有非吃子着。【按键】假设 A、B、C、D 都合法，但只有 D 能迅速让 alpha 不低于 beta，或让 beta 不高于 alpha，于是停止该节点的剩余候选。若 D 在最后，前面三棵子树已经搜过；若 D 先搜，同样的边界能更早建立。排序不删候选，也不改变 Minimax 结论；它只用过去的搜索经验猜“哪手更可能快速截断”。',
      sources: ['xiangqi_ai.cpp:1271-1302'], takeaway: '排序不改答案；它让可能收紧边界的着更早接受搜索。'
    },
    {
      id: 's21a', title: '三本经验账：同一层、上一着、长期记录', eyebrow: '安静着排序 · 真实索引与更新', layout: 'compare',
      lead: '三种经验都只在安静着真正触发 Alpha-Beta 截断时更新。',
      table: {headers:['经验','按什么查','记什么'], rows:[
        ['killer','killer_moves[ply][0 / 1]','同一搜索层数最近奏效的两手安静着'],
        ['counter','counter_move[上一着起点][上一着终点]','这组完整起终点之后，哪手安静着曾触发截断'],
        ['history','history_table[当前着起点][当前着终点]','这组起终点长期触发截断的累计经验']
      ]},
      code: `bonus = depth * depth;
history[successful_quiet] += bonus;
for (quiet : earlier_searched_quiets)
  history[quiet] -= bonus;
history = clamp(history, -(1<<20), +(1<<20));`,
      cards: [
        {title:'killer 两槽',text:'新着进槽 0，原槽 0 下移槽 1；不按局面或棋种分组。'},
        {title:'counter 的键',text:'使用上一着的 r1,c1,r2,c2 四坐标，不是只看目标格。'},
        {title:'history 的边界',text:'深度越大，奖惩 depth² 越大；上下封顶 ±2²⁰，没有周期衰减。'}
      ],
      steps: ['killer 在每个 ply 保留两手，跨该层的不同局面复用', 'counter 用上一着的完整四坐标查一手反制', 'history 用当前候选的四坐标累加正负经验', '吃子即使触发截断，也不更新这三本账'],
      notes: '第一本是 killer。键只有当前 ply，也就是从根节点向下数的搜索层数；每层两个槽位。新的成功安静着进槽零，原槽零下移到槽一。它的含义是“同一层的其他局面中，这手曾奏效”。【按键】第二本是 counter。它用上一着的起点行列和终点行列四个坐标作键，记住其后曾触发截断的安静着；它不按上一着的棋种或单独目标格分类。【按键】第三本是 history。它用当前候选自己的起终点四坐标作键。深度为 depth 的安静着触发截断，就加 depth 的平方；在同一节点里比它更早实际搜过却未截断的安静着，各减同样的分。分数封顶在正负二的二十次方，没有周期衰减；设置新棋盘时才清零。三种经验都只由触发截断的安静着更新；吃子不写入它们。',
      sources: ['xiangqi_ai.cpp:325-327','xiangqi_ai.cpp:416-425','xiangqi_ai.cpp:1262-1269','xiangqi_ai.cpp:1446-1505','xiangqi_ai.cpp:1746-1760'], takeaway: '三本账分别回答：同一层常奏效、针对上一着常奏效、这组起终点长期常奏效。'
    },
    {
      id: 's21b', title: '五个候选，怎样排成搜索队列？', eyebrow: '走法排序 · 真实分档', layout: 'compare',
      lead: '下列数值只是排序键，不是局面分，也不代替递归搜索。',
      table: {headers:['候选','命中信号','源码排序分'], rows:[
        ['A：炮吃车，SEE 非负','好吃子','10,000,000 + 1000×10 − 450 = 10,009,550'],
        ['B：安静着','killer 槽 0','9,000,000'],
        ['C：安静着','counter','7,000,000'],
        ['D：安静着','history','12,500'],
        ['E：安静着','history','−3,000']
      ]},
      code: `if (move == tt_move)      score = 300000000;
else if (good_capture)       score = 10000000 + victim*10 - attacker;
else if (move == killer1)    score = 9000000;
else if (move == killer2)    score = 8000000;
else if (move == counter)    score = 7000000;
else                         score = history[from][to];`,
      cards: [
        {title:'本例队列',text:'A 好吃子 → B killer → C counter → D history → E history'},
        {title:'若命中多个信号',text:'代码是 else-if：先命中的高档生效，不把 killer、counter、history 相加。'},
        {title:'吃子与经验分开',text:'吃子先走吃子分支；killer / counter / history 排的是安静着。'}
      ],
      steps: ['TT 最佳着若存在，用三亿分放在最前', '好吃子用一千万档，并用被吃子与攻击子价值细排', 'killer 两槽九百万/八百万，counter 七百万', '剩余安静着直接按 history 分数降序'],
      notes: '用一次具体排序收束。A 是炮吃车，被吃车价值一千，进攻炮价值四百五十，SEE 不为负；因此它的排序键是一千万加一千乘十减四百五十，得一千零九万九千五百五十。B 命中 killer 槽零，九百万；C 命中 counter，七百万；D 和 E 只有 history，分别是一万二千五百与负三千。所以本例队列是 A、B、C、D、E。【按键】这些大数只是排序档位，不是红黑优势分。同一手若同时命中 killer 和 counter，代码取先命中的 killer，不把分数相加。另一个边界是：明显亏损的贵子吃便宜子被放在约一百万档；history 可封顶到一百零四万八千五百七十六，因此极高 history 安静着与这类坏吃子可能按实际数值混排，不存在“所有吃子永远在所有安静着前”的绝对规则。最终每个候选仍要由递归搜索检验。',
      sources: ['xiangqi_ai.cpp:91-100','xiangqi_ai.cpp:1271-1302'], takeaway: '排序分只决定尝试顺序：好吃子先建边界，三类经验再安排安静着。'
    },
    {
      id: 's25', title: '我们现在会算明白，下一步要学会算得更深', eyebrow: '过渡 · 下一章', layout: 'map',
      lead: '目前的主干：Minimax 理解对手，Alpha-Beta 利用边界，静止搜索稳定叶子，置换表复用证据，排序和迭代加深帮我们按时得到更好答案。',
      cards: [
        {title: '已完成', text: '完整的搜索逻辑、证明性剪枝、战术叶子、缓存、排序和按时交卷'},
        {title: '下一个问题', text: '即使顺序很好，候选仍然太多。哪些路可以先少看、暂时跳过？'},
        {title: '风险提示', text: '下一章的方法将逐步从“边界可证”走向“经验取舍”，必须同时讲清漏棋风险'}
      ],
      steps: ['本章获得：考虑对手、利用边界、稳定叶子、复用记忆、按时交卷', '即使如此，搜索深度仍然受限', '下章将处理三类问题：找领路着、便宜试探、经验裁剪'],
      notes: '回顾一下，我们已经走了很远。【按键】Minimax 让机器把对手的选择放进自己的思考；Alpha-Beta 让它在证据足够时不必算准一条差路；QS、SEE 和将军延伸降低了恰好停在战术中间的风险；TT 和排序让已经得到的经验反复帮忙；迭代加深让它在时间到之前始终有完整答案。【按键】但就算这样，树仍然太大。【按键】下一章我们会继续问：能不能先用便宜方式试探，不符合预期再补搜？能不能让排名靠后的路少看几层？从那一刻开始，我们也从可证的边界走进了有漏棋可能的经验判断。',
      sources: ['xiangqi_ai.cpp:1123','xiangqi_ai.cpp:1030','xiangqi_ai.cpp:1156','xiangqi_ai.cpp:1262','xiangqi_ai.cpp:1545'], takeaway: '先有可靠的主干，再讨论如何用经验换深度。'
    }
  ]
});
