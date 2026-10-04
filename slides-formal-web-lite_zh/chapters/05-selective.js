window.XQ_CHAPTERS = window.XQ_CHAPTERS || [];

window.XQ_CHAPTERS.push({
  id: '05',
  title: '向前推演：把时间花在值得的路上',
  slides: [
    {
      id: 'a01',
      title: '浅层已经探过路，还能给深层留下些什么？',
      eyebrow: '第三阶段 · 搜索的后半程',
      layout: 'cards',
      lead: '上一轮留下走法、分数和一条最可能的主线；下一轮可以用这些结果少走弯路。',
      cards: [
        { title: '节点里没有领路着', text: '先便宜地找一手，免得把差着排在前面。' },
        { title: '候选已经排好', text: '先问后面的走法能不能挑战当前最好。' },
        { title: '开始新一轮深度', text: '先猜这轮分数仍在上一轮附近。' }
      ],
      steps: ['节点里没领路着：先找“谁先搜”', '候选已经排好：再问“能否超过当前最好”', '新一轮深度开始：最后猜“分数是否仍在附近”'],
      notes: '上一轮浅层搜索已经完成了。它留下的结果，能怎样帮助下一次更深的搜索？【停顿】第一种情况发生在深层节点：置换表里没有最佳着，我们缺的是“先搜谁”。第二种情况里，候选已经排好，我们想知道“后面的着值不值得完整搜索”。第三种情况发生在根节点开始新一轮时，我们想猜“这轮分数大概还在不在上一轮附近”。这三件事看起来都是先便宜地试一下，但它们试探的对象、作用范围和失败后的动作都不同。我们先看第一种：连领路着都没有。',
      sources: ['xiangqi_ai.cpp:1241', 'xiangqi_ai.cpp:1411', 'xiangqi_ai.cpp:1554'],
      takeaway: '先说清试探对象，再给技术命名。'
    },
    {
      id: 'a02',
      title: '没有领路着：先少看几层，只为找一手',
      eyebrow: '内部迭代加深',
      layout: 'tree',
      lead: '当前节点很深，置换表里却没有最佳着；随便挑第一手会让 Alpha-Beta 很晚才得到强边界。',
      tree: {
        kind: 'ordering',
        root: '深度 8：没有 TT 最佳着',
        branches: [
          { label: '浅搜到深度 4', value: '找到领路着 B' },
          { label: '重新排序', value: 'B → A → C → D' },
          { label: '正式深搜', value: '从 B 开始' }
        ]
      },
      code: `if (!tt_move.is_valid() && depth >= 6) {
  auto iid = shallow_search(depth - 4, alpha, beta);
  tt_move = iid.move;       // 用来排序
}`,
      steps: ['深度 8、TT 没有领路着', '先浅搜到深度 4，只取最佳着 B', '把 B 移到队首，再开始目标深度搜索', '这叫内部迭代加深（IID）'],
      notes: '当前节点很深，置换表又没有最佳着。若按原顺序深搜，差着可能排在前面，Alpha-Beta 要搜索许多分支以后才能建立强边界。源码在深度至少为 6 时，先把目标深度减四做一次便宜浅搜，找到 B，再把 B 拉到队首。【按键】如果 B 的排序判断有效，正式深搜会更早得到好分数，后面的分支也更早截断；省下的深层节点可以抵回这次浅搜成本。这就是内部迭代加深，Internal Iterative Deepening，IID。它只借用浅搜找到的领路着，正式结果仍由原目标深度决定。它发生在树内某个节点；根节点一层层按时交卷的迭代加深解决的是另一件事。现在第一手已经认真搜完，后面的着还需要逐一求精确分吗？',
      sources: ['xiangqi_ai.cpp:1241-1247'],
      takeaway: 'IID 的产物是领路着，不是最终分数。'
    },
    {
      id: 'a03',
      title: '已有最好值：后面的走法先来挑战它',
      eyebrow: '主要变例搜索',
      layout: 'tree',
      lead: '排序后的第一手形成当前主要变例；后续着先用整数零窗口回答：“你能超过当前最好吗？”',
      tree: {
        kind: 'alphabeta',
        root: '当前最好：α = 36',
        branches: [
          { label: '第 1 手', value: '完整窗口 → 36' },
          { label: '第 2 手', value: '[36, 37] 试探 → 没超过' },
          { label: '第 3 手', value: '[36, 37] 试探 → 超过，补搜' }
        ]
      },
      code: `first move: search(alpha, beta)
later move: search(alpha, alpha + 1)
if (score > alpha && score < beta)
    search(alpha, beta)      // 挑战成功才求精确`,
      steps: ['第一手没有参照物，用完整窗口搜索', '后续着先用零窗口挑战当前最好', '没有超过：我们已知道它不值得选', '超过但尚未截断：恢复完整窗口求精确分', '这叫主要变例搜索（PVS）'],
      notes: '第一手没有参照物，只能用完整窗口搜索；双方当前最佳应对连成的路线，就是主要变例。它得到 36 分以后，后续着真正要先回答的只有一个问题：“能否超过 36？”【按键】整数分数中，[36,37] 之间没有第三个值。这个零窗口只分辨门槛两侧，子节点一旦证明“不超过”或“至少达到”，便能更早利用 Alpha-Beta 边界停止搜索，因此证伪一手挑战通常比求出它的精确分便宜。返回不超过 36，这手退出竞争；返回至少 37，它挑战成功。若分数尚未达到 beta 截断界，就恢复完整窗口重搜，求出新主要变例的精确分。这就是主要变例搜索，Principal Variation Search，PVS；最小方对称使用 [beta-1,beta]。它省下的是大多数失败挑战的精确搜索，代价是排序不准时会多做一次重搜。',
      sources: ['xiangqi_ai.cpp:1410-1444'],
      takeaway: 'PVS 用窄窗挑战当前最好，挑战成功才补精度。'
    },
    {
      id: 'a04',
      title: '新一轮深度：先猜分数不会突然远走',
      eyebrow: '期望窗口',
      layout: 'compare',
      lead: '全窗口要分辨很大的分数范围；深度 7 先围绕上一轮结果开小窗，让两侧更早形成截断。',
      cards: [
        { title: '上一轮', text: '深度 6：分数 120（示意）' },
        { title: '先试小窗', text: '深度 7：先搜 [90, 150]' },
        { title: '超出上界', text: 'fail-high：扩大上界后重搜' },
        { title: '仍不收敛', text: '继续扩窗；必要时回到全窗' }
      ],
      code: `delta = 30;
alpha = prev_score - delta;
beta  = prev_score + delta;
while (score <= alpha || score >= beta) {
  widen_window();
  if (delta > 1000) use_full_window();
}`,
      steps: ['上一轮深度 6 得到 120（教学分）', '新一轮先搜索 [90, 150]', '结果越过上界：这次猜窄了', '扩大窗口并重新搜索，必要时退回全窗', '这叫期望窗口（Aspiration Window）'],
      notes: '这里的 120、90、150 是演示窗口变化的教学数字。若深度 7 一开始就给很宽的窗口，搜索必须在更大的分数范围内分辨结果；以上一轮 120 为中心先搜 [90,150]，alpha 和 beta 离预期结果更近，搜索树两侧更容易较早触界，从而少展开节点。【按键】源码把 delta 设为 30。结果小于等于 alpha，叫 fail-low；大于等于 beta，叫 fail-high。任何一侧失败都说明这次猜窄了，程序扩大窗口重搜；delta 超过 1000 时退回全窗。相邻深度分数接近时，小窗节省节点；新战术让分数跳变时，代价是扩窗和重复搜索。这就是期望窗口，Aspiration Window。PVS 节省同一节点中后续候选的精确搜索；期望窗口缩小的是根节点新一轮首先要分辨的分数范围。',
      sources: ['xiangqi_ai.cpp:1554-1583'],
      takeaway: '期望窗口猜整轮分数，猜错就扩窗重搜。'
    },
    {
      id: 'a05',
      title: '三次“先试试”，试的不是一件事',
      eyebrow: '把相似外形拆开',
      layout: 'table',
      lead: '一个找顺序，一个挑战最好值，一个猜整轮分数。',
      table: {
        headers: ['发生位置', '真正的问题', '便宜动作', '何时补算'],
        rows: [
          ['深层节点', '第一手先搜谁？', 'IID 浅搜找领路着', '正式搜索始终按目标深度'],
          ['同一节点的后续着', '能超过当前最好吗？', 'PVS 零窗口挑战', '进入有效窗口时全窗重搜'],
          ['根节点的新深度', '分数还在上轮附近吗？', '期望小窗口', 'fail-low / fail-high 后扩窗']
        ]
      },
      steps: ['IID 找的是领路着', 'PVS 挑战的是当前最好值', '期望窗口猜的是新一轮分数范围'],
      notes: '现在用三个问题把它们分开。第一，当前节点第一手先搜谁？IID 给我们的产物是一着领路棋。第二，后续着能不能超过当前最好？PVS 先给我们一个界。第三，新一轮分数还在不在上一轮附近？期望窗口猜的是整轮根搜索的范围。它们都可能多做一次搜索，但共同思路是用便宜试探换取后续节省，并不是同一套失败逻辑。到这里，试探不符合预期时我们仍愿意补搜，主要改变的是效率。接下来风险会提高：为了看得更深，我们开始少看，甚至不看某些路。',
      sources: ['xiangqi_ai.cpp:1241-1247', 'xiangqi_ai.cpp:1411-1444', 'xiangqi_ai.cpp:1554-1583'],
      takeaway: '辨认技术，要看它在回答什么问题。'
    },
    {
      id: 'a06',
      title: '想再看深一点，就必须承担判断风险',
      eyebrow: '选择性搜索 · 风险阶梯',
      layout: 'cards',
      lead: 'Alpha-Beta 是证据足够后的剪枝；下面这些是经验判断，可能漏棋。',
      cards: [
        { title: '第一阶：少看几层', text: '候选仍然搜索，只是先降低深度。' },
        { title: '第二阶：跳过一手', text: '对某个候选，经验判断它不值得展开。' },
        { title: '第三阶：跳过整个节点', text: '甚至不生成全部候选，直接返回一个界。' }
      ],
      steps: ['少看几层：候选仍会被搜索', '跳过一手：某个候选不再展开', '跳过整个节点：不再逐一搜索候选', '越往后省得越多，误判代价也越大'],
      notes: '前面的 Alpha-Beta 在固定搜索树和固定评估下，不改变 minimax 的结果。现在我们要开始改变真正展开的树，风险也从这里出现。第一阶只是少看几层；第二阶会直接跳过某个候选；第三阶甚至尝试判断整个节点。越往右，省下的搜索越多，判断错时漏掉的内容也越多。对每一种方法，我们都问同样四件事：什么时候触发，实际做什么，凭什么这样猜，以及可能漏掉什么。先从最温和的一阶开始：排序靠后的安静着，能不能先少看几层？',
      sources: ['xiangqi_ai.cpp:1177-1239', 'xiangqi_ai.cpp:1337-1444'],
      takeaway: '选择性搜索用漏棋风险换取更深的重点搜索。'
    },
    {
      id: 'a07',
      title: '排得晚的安静着：先少看，但给它翻身机会',
      eyebrow: '后期着法缩减 · Late Move Reductions（LMR）',
      layout: 'tree',
      lead: '深度不浅、排名靠后、不吃子、不将军、不是 killer：先以较浅深度试探。',
      tree: {
        kind: 'ordering',
        root: '原目标深度 7',
        branches: [
          { label: '第 1 手', value: '完整深度 6' },
          { label: '第 2、3 手', value: '窄窗，通常不缩减' },
          { label: '第 4 手以后普通静着', value: '先少搜 R 层' },
          { label: '意外超过当前最好', value: '恢复深度，再按需全窗' }
        ]
      },
      code: `if (late_quiet_move && !in_check && !gives_check) {
  R = LMR_TABLE[depth][move_index]; // 暂时少搜的层数
  R += history_is_bad; R -= history_is_good;
  score = search(depth - 1 - R, narrow_window);
  if (score challenges_best)
    score = search(depth - 1, narrow_window);
}`,
      steps: ['前三手按正常深度建立参照', '第四手以后的普通静着先少看几层', 'history 越好，缩减越少；越差，缩减越多', '减深结果挑战成功：恢复完整深度', '仍进入有效窗口：再做全窗搜索'],
      notes: '排序排到第四以后的普通静着，要不要一刀删掉？我们先采用更保守的办法：仍然搜，只是少看几层。这叫后期着法缩减，Late Move Reductions，简称 LMR。源码要求深度至少为 3、候选排在第三手之后、当前没有被将、这手不吃子、不是 killer，走完也不将军。表格用当前深度和候选排名作输入，给出 R；R 就是这次暂时少搜的层数。局面越深、候选越靠后，R 通常越大；history 好就少减，history 差就多减。【按键】如果减深搜索意外超过当前最好，这手得到一次翻身机会：先恢复完整深度的窄窗搜索；分数仍落在 alpha 和 beta 之间，再用全窗求精确。一手安静棋可能要很深才显出价值，所以减深仍可能低估它。下一步风险更高：有些排得太晚的静着，我们连浅搜都不做。',
      sources: ['xiangqi_ai.cpp:281-288', 'xiangqi_ai.cpp:1395-1444'],
      takeaway: 'LMR 先减深；被低估的候选仍有恢复搜索的通道。'
    },
    {
      id: 'a08',
      title: '浅层候选太多：过晚的普通着先不看',
      eyebrow: '后期着法剪枝 · Late Move Pruning（LMP）',
      layout: 'cards',
      lead: '在浅层、非将军节点里，前面已经搜过许多更优先的普通着，过晚静着被直接跳过。',
      cards: [
        { title: '允许触发', text: '非根节点；深度 ≤ 8；当前未被将；不是吃子；不是 killer。' },
        { title: '数量门槛', text: '已尝试候选数 > 3 + depth²。' },
        { title: '动作', text: '这一手不 make、不递归，直接看下一候选。' },
        { title: '可能漏掉', text: '排序靠后，却需要安静铺垫才显出价值的好棋。' }
      ],
      steps: ['前面的高优先级着照常搜索', '候选数越过 3 + depth² 后，过晚普通静着被跳过', '吃子与 killer 不由这条规则跳过', '代价：可能漏掉排序靠后的安静好棋'],
      notes: '浅层节点可能有很多普通静着。若每一手都 make、递归、undo，搜索预算会平均耗在长尾候选上。前面的高优先级着照常搜索；尝试数量超过 3+depth² 后，符合条件的晚到静着直接跳过，省掉这手的整棵子树。这叫后期着法剪枝，Late Move Pruning，简称 LMP。LMR 还会减深试探，LMP 连浅搜都省掉，因此更依赖排序质量。正被将时要检查全部应将；吃子和 killer 带有更强信号。源码还检查 best_score：如果当前最好结果仍接近己方被杀，后续着可能是救命棋，此时关闭 LMP。它用漏掉晚到安静好棋的风险，换取把深度留给队首候选。下一种方法不看排名，而看普通静着即使得到乐观余量，是否仍追不上窗口。',
      sources: ['xiangqi_ai.cpp:1337-1343'],
      takeaway: 'LMP 用排名和浅层条件跳过过晚静着。'
    },
    {
      id: 'a09',
      title: '就算给它一笔乐观余量，也追不上当前门槛',
      eyebrow: '无益剪枝 · Futility Pruning',
      layout: 'compare',
      lead: '静态评分离 alpha / beta 太远，普通静着即使得到经验余量，仍不像能改变结论。',
      cards: [
        { title: '当前静态分', text: 'eval = 40（示意）' },
        { title: '浅层余量', text: '100 + 100 × depth' },
        { title: '当前门槛', text: 'alpha = 500（示意）' },
        { title: '判断', text: 'eval + margin ≤ alpha → 跳过这手普通静着' }
      ],
      code: `if (depth <= 6 && !in_check && !is_capture
    && moves_count > 1) {
  margin = 100 + 100 * depth;
  if (eval + margin <= alpha) skip_move();
}`,
      steps: ['当前静态分明显落后于 alpha', '给普通静着一笔 100 + 100×depth 的乐观余量', '加完余量仍够不到 alpha：跳过这手', '代价：静态评分可能低估延迟兑现的收益'],
      notes: '我们先站在最大方看，最小方做对称判断。40 和 500 是教学分。当前静态分落后很多，如果仍为每个普通静着递归，只为最终证明它够不到 alpha，会反复展开无法改变选择的分支。源码给这手一笔 100+100×depth 的乐观余量；加完仍不超过 alpha，就省掉 make、递归与整棵后续子树。这叫无益剪枝，Futility Pruning。它只用于深度不超过 6、当前未被将、非吃子且不是第一手的候选。代价来自静态分的盲区：腾挪、控制或配合可能几步以后才兑现，于是看似无益的安静棋可能被漏掉。接下来处理另一类数量很多的候选：吃子。',
      sources: ['xiangqi_ai.cpp:1345-1358'],
      takeaway: 'Futility 用静态分与余量判断一手普通着是否仍有希望。'
    },
    {
      id: 'a10',
      title: '前面用于筛选和排序的 SEE，还能直接剪枝吗？',
      eyebrow: '从辅助判断到跳过候选',
      layout: 'board',
      lead: '同一笔车吃炮交换已经算出 SEE < 0；这里关注更强的动作：主搜索能否干脆不搜。',
      boards: [
        {
          fen: '4k4/9/9/2n6/c8/R8/4P4/9/9/4K4 w',
          caption: '红方走 · 红车准备吃 (4,0) 黑炮',
          orientation: 'red',
          highlights: [{ square: 'a5', kind: 'from' }, { square: 'a4', kind: 'capture' }, { square: 'c3', kind: 'focus' }],
          arrows: [{ from: 'a5', to: 'a4', kind: 'capture' }],
          annotations: [{ square: 'c3', text: '黑马可回吃' }]
        },
        {
          fen: '4k4/9/9/2n6/R8/9/4P4/9/9/4K4 b',
          caption: '红车吃炮后 · 轮到黑方',
          orientation: 'red',
          highlights: [{ square: 'a4', kind: 'to' }, { square: 'c3', kind: 'from' }],
          arrows: [{ from: 'c3', to: 'a4', kind: 'capture' }]
        },
        {
          fen: '4k4/9/9/9/n8/9/4P4/9/9/4K4 w',
          caption: '黑马回吃后 · 红车消失',
          orientation: 'red',
          highlights: [{ square: 'a4', kind: 'to' }],
          annotations: [{ square: 'a4', text: '净物料变化 −550' }]
        }
      ],
      steps: ['第一层只看到红车吃炮：教学账本 +450', '黑马从 (3,2) 回吃 (4,0) 的红车，马腿 (3,1) 为空', '两着后相对初始局面：+450 −1000 = −550', '这只是基础子力账本，不是当前 evaluate() 的完整 PST 分数'],
      notes: '前面已经用这笔交换讲清 SEE：红车从 (5,0) 吃 (4,0) 黑炮，(3,2) 黑马随后回吃红车，所以目标格交换账为负。在 QS 中，这个结果用于过滤叶子候选；在主搜索排序中，它只让该吃子晚一点搜索。\n\n[按键] 现在把动作再加强一级：浅层主搜索能不能根据同一个 SEE 结果，直接省掉这手的递归子树？两着后的基础子力变化 450−1000=−550 仍帮助我们确认这是明显亏损的交换；下一页只讲什么时候允许真正跳过，以及怎样防止判断过猛。',
      sources: ['象棋教学局面核验.md:B', 'xiangqi_ai.cpp:91-106', 'xiangqi_ai.cpp:931-1027'],
      takeaway: 'SEE 先辅助叶子过滤与排序；SEE pruning 才在受限条件下真正跳过主搜索候选。'
    },
    {
      id: 'a10b',
      title: '看起来能吃，不代表这笔交换划算',
      eyebrow: '静态交换评估剪枝 SEE pruning',
      layout: 'cards',
      lead: '浅层非将军节点中，贵子吃便宜子且目标格连续交换明显亏损，这手可被跳过。',
      cards: [
        { title: '先筛形状', text: '深度 ≤ 4；吃子；当前未被将。' },
        { title: '再看价格', text: '受害子价值 < 进攻子价值。' },
        { title: '模拟目标格交换', text: 'SEE < -50，认为明显亏损。' },
        { title: '仍有风险', text: '弃子引将、腾线、做杀等补偿可能不在静态交换里。' }
      ],
      code: `if (depth <= 4 && is_capture && !in_check) {
  if (victim_value < attacker_value && see(move) < -50)
    skip_move();
}`,
      steps: ['候选是吃子，也先比较攻击子与受害子价格', '再用 SEE 模拟目标格上的连续交换', 'SEE < -50：把明显亏损的吃子跳过', '代价：目标格账本可能看不到全局战术补偿'],
      notes: '这一页承接前面用途表的第三行，不再重讲 SEE 怎样计算。主搜索只有在非根、深度不超过 4、当前未被将、候选确实是贵子吃便宜子时，才继续检查 SEE；小于负五十才在第一遍跳过这手递归。负五十比 QS 的零门槛多留了一点余量，因为这里不是少扩展一条叶子交换，而是在主搜索中真正不搜这个候选。\n\n[按键] 风险仍然存在：SEE 只计算目标格交换，弃子引将、腾线、闪击和后续做杀可能带来账本外补偿。后面的两遍搜索会在最好结果异常或剪后没有合法着等情况下关闭这类局部跳过，重新从候选表开头搜索。到这里，我们省掉的是单个候选；接下来尝试在生成全部候选以前判断整个节点。',
      sources: ['xiangqi_ai.cpp:1362-1370', 'xiangqi_ai.cpp:931-1027'],
      takeaway: 'SEE pruning 用目标格交换账本过滤明显亏损的吃子。'
    },
    {
      id: 'a11',
      title: '再大胆一步：能否直接判断整个节点？',
      eyebrow: '整节点经验判断',
      layout: 'cards',
      lead: '三个问题，分别从“已经很好”“看起来太差”“让一拍仍然很好”出发。',
      cards: [
        { title: '已经好得足够多？', text: '静态分减去余量仍越过 beta。' },
        { title: '已经差得太远？', text: '先用静止搜索验证，仍翻不过 alpha。' },
        { title: '让一拍仍足够好？', text: '做一次搜索中的假空着，再看是否仍越界。' }
      ],
      steps: ['静态分已经好得足够多：能否直接返回一个界？', '静态分看起来太差：能否先用 QS 复核？', '假设让一拍仍然够好：能否认为真实走棋也够好？', '共同限制：非根、未被将，并避开将杀分区间'],
      notes: '逐一检查候选至少要生成走法，并为每手执行 make、递归和 undo。整节点判断试图在这些工作开始前，用更便宜的证据返回一个足以截断的界。这里有三种证据：静态分扣掉余量仍很好；静态分太差，再用 QS 复核仍翻不过窗口；假设让一拍，对手仍无法把结果拉回窗口。它们只用于非根、未被将且远离将杀分的节点。命中时省掉几乎整棵节点子树，误判时也可能整批漏掉候选。先看静态上已经足够好的情况。',
      sources: ['xiangqi_ai.cpp:1177-1239'],
      takeaway: '整节点裁剪省得最多，也需要最谨慎的触发条件。'
    },
    {
      id: 'a12',
      title: '静态上已经越过界：留出余量后再判断',
      eyebrow: '反向无益剪枝 · Reverse Futility Pruning（RFP）',
      layout: 'compare',
      lead: '普通 Futility 判断一手能否追上；RFP 用保守后的静态分判断整个节点能否直接截断。',
      cards: [
        { title: '最大方静态分', text: 'eval' },
        { title: '保守扣减', text: 'margin = 80 × depth' },
        { title: '仍越过 beta', text: 'eval - margin ≥ beta' },
        { title: '直接返回', text: '返回一个足够截断的界' }
      ],
      code: `if (!is_root && depth <= 7 && !in_check) {
  margin = 80 * depth;
  if (eval - margin >= beta)
    return eval - margin;
}`,
      steps: ['静态分先越过 beta', '扣掉 80×depth 的保守余量', '仍越界：对整个节点返回一个截断界', '风险：静态高分可能掩盖强制反击'],
      notes: '普通 Futility 对候选逐手判断；RFP 在生成和搜索候选以前判断整个节点。以最大方为例，静态分减去 80×depth 的保守余量后仍达到 beta，程序直接返回一个足以让祖先截断的界，于是省掉本节点的走法生成和后续子树。这就是反向无益剪枝，Reverse Futility Pruning，RFP；最小方对称处理。源码只用于非根、深度不超过 7、未被将且远离将杀分的窗口。它依赖静态评估足以代表浅层局势；若高分掩盖了对手的强制反击，整棵被省掉的子树里可能藏着推翻结论的变化。下一页从静态分很差的节点出发，并增加一次战术复核。',
      sources: ['xiangqi_ai.cpp:1177-1186'],
      takeaway: 'RFP 用“静态优势减余量仍越界”判断整个节点。'
    },
    {
      id: 'a13',
      title: '静态上差得太远：先让战术搜索复核一次',
      eyebrow: '剃刀剪枝 · Razoring',
      layout: 'tree',
      lead: '浅层节点离 alpha 很远，先转入静止搜索；连眼前战术也翻不过来，才提前返回。',
      tree: {
        kind: 'alphabeta',
        root: 'eval + 200×depth ≤ alpha',
        branches: [
          { label: '直接放弃？', value: '太冒险' },
          { label: '先做 QS', value: '检查吃子与应将' },
          { label: 'QS 仍 ≤ alpha', value: '返回这个界' },
          { label: 'QS 翻上来', value: '继续正常主搜索' }
        ]
      },
      code: `if (depth <= 3 && !in_check
    && eval + 200 * depth <= alpha) {
  q = quiescence(alpha, beta);
  if (q <= alpha) return q;
}`,
      steps: ['静态分加余量仍远低于 alpha', '先进入 QS 检查眼前吃子与应将', 'QS 仍翻不过 alpha：提前返回', 'QS 翻上来：回到正常主搜索'],
      notes: '以最大方为例。深度不超过 3，静态分加上 200×depth 的余量仍到不了 alpha；若继续完整主搜索，大量工作可能只是证明这个节点确实太差。源码先做更便宜的静止搜索，检查眼前吃子与被将时的全部应将。QS 仍不越过 alpha，就提前返回这个界，省掉余下普通着的主搜索；QS 翻上来则恢复正常搜索。这叫剃刀剪枝，Razoring。代价是 QS 的视野集中在眼前战术，需要安静铺垫的翻盘仍可能被漏掉。最小方对称处理。下一种整节点试探把“让一拍”作为搜索假设。',
      sources: ['xiangqi_ai.cpp:1188-1199', 'xiangqi_ai.cpp:1030-1118'],
      takeaway: 'Razoring 先用 QS 复核“静态太差”，仍翻不过界才返回。'
    },
    {
      id: 'a14b',
      title: '让一拍，局面还够好吗？',
      eyebrow: '空着剪枝 · Null Move Pruning（NMP）',
      layout: 'tree',
      lead: '临时只交换行棋方与哈希轮次，做一次大幅减深的零窗口搜索；随后完整撤销。',
      tree: {
        kind: 'alphabeta',
        root: '当前节点：未被将，深度 ≥ 3',
        branches: [
          { label: '假设空着', value: '切换行棋方，不移动棋子' },
          { label: '减深零窗', value: '对手仍无法把结果拉回' },
          { label: '越过界', value: '尝试截断' },
          { label: '深度 ≥ 10', value: '再做一次验证搜索' }
        ]
      },
      code: `make_null_move();            // 搜索内部假设
R = reduced_plies(depth, eval); // 额外少搜的层数
score = search(depth - 1 - R, narrow_window,
               /* allow_null = */ false);
undo_null_move();
if (cutoff && depth >= 10)
  verify_without_another_null();`,
      steps: ['棋子不动，只在搜索状态中切换行棋方与哈希轮次', '只在非根、剩余深度至少 3 且未被将时尝试', '空着子搜索禁止再次空着，不能连续两次 NMP', '深度至少 10 时，越界后再做降深验证搜索', '这些限制只缓解残局迫走风险，不能彻底避免误判'],
      notes: '完整展开一个看起来已经足够好的节点，仍要逐手证明对手无法把结果拉回 beta。空着剪枝，Null Move Pruning，NMP，改做一次便宜的反事实试验：棋子不动，只切换行棋方；如果主动浪费一拍以后，减深零窗搜索仍越过 beta，就把它作为整个节点足够好的证据，从而省掉真实候选的完整子树。源码只在非根、剩余深度至少 3、当前未被将、允许空着且远离将杀分时尝试。公式中的 1 是让出的这一拍，R 是额外少搜层数，从 3+depth/6 起，并随静态分越界幅度增加。\n\n[按键] 残局等着或迫走会挑战这个前提：真实规则强迫一方走子，一走反而变差，“让一拍仍好”不能代表真实着法。当前实现用三点缓解风险：根节点不用；接近叶子、剩余深度小于 3 时不用；空着子搜索把 allow_null 设为 false，禁止连续两次 NMP。深度至少 10 时，越界后还会回到原局面做一次降深验证。这些措施只能降低风险，不能彻底防止困毙或迫走误判。空着只存在于搜索状态，最终输出仍来自合法候选。',
      sources: ['xiangqi_ai.cpp:598-626', 'xiangqi_ai.cpp:1201-1239'],
      takeaway: '残局迫走会挑战空着假设；深度门槛、禁止连续空着和高深验证只能缓解风险。'
    },
    {
      id: 'a15',
      title: '漏掉救命棋怎么办？再跑一遍候选',
      eyebrow: '局部两遍搜索',
      layout: 'code',
      lead: '第一遍允许三类“跳过候选”；命中任一补搜条件时，从候选表开头重跑，并关闭这三类局部跳过。',
      code: `need_second_pass = near_losing_mate(best_score)
                || (pruned_any && legal_searched == 0);
for (pass : {pruning_on, pruning_off_if_needed}) {
  for (move : ordered_moves_from_beginning) {
    if (pass == pruning_on)
      maybe_skip_by_LMP_Futility_SEE();
    search_normally(move); // 第二遍可能重复已搜着
  }
}`,
      steps: ['第一遍允许 LMP、Futility、SEE pruning 跳过候选', '触发一：最好分仍接近己方被杀', '触发二：剪过候选，而且没有搜到任何合法着', '命中任一条件，第二遍从候选表开头重跑并关闭三类跳过', '被跳过着得到搜索；部分已搜着也会重复递归'],
      notes: 'LMP、Futility 和 SEE pruning 省掉候选子树，但同一份经验判断也可能把救命棋或全部合法着跳过。第一遍结束后，如果最好分仍接近己方被杀，或者确实剪过候选却一着也没搜到，程序触发第二遍。【按键】第二遍把候选下标重新置零，从排序表开头再跑一遍，同时把 allow_pruning 设为 false，只关闭上述三类“直接跳过候选”。这样原先被跳过的着会得到搜索，第一遍已经搜过的合法着也可能再次递归；保险绳的代价就是这些重复节点。LMR 仍可减深，Alpha-Beta 继续截断；进入走法循环以前执行的 RFP、Razoring 和 NMP 也不会被撤销。因此第二遍只针对三类局部跳过增加保障，无法覆盖其他选择性判断。最后再看一个每个保留节点都会反复承担的成本：车炮直线查询。',
      sources: ['xiangqi_ai.cpp:1310-1324', 'xiangqi_ai.cpp:1337-1370', 'xiangqi_ai.cpp:1512-1515'],
      takeaway: '第二遍从头重跑并关闭三类局部跳过，用重复搜索换取补漏机会。'
    },
    {
      id: 'a18',
      title: '朴素做法：每次都沿线找阻挡',
      eyebrow: '车炮直线 · 逐格扫描基线',
      layout: 'board',
      lead: '回答一条炮路，先找炮架，再找炮架后的第一枚棋子。',
      boards: [
        {
          fen: '3k5/9/4r4/9/9/4P4/9/4C4/9/4K4 w',
          caption: '红炮在 (7,4) · 向上遇 (5,4) 炮架，再遇 (2,4) 黑车',
          orientation: 'red',
          highlights: [{ square: 'e7', kind: 'from' }, { square: 'e5', kind: 'focus' }, { square: 'e2', kind: 'capture' }],
          arrows: [{ from: 'e7', to: 'e2', kind: 'capture' }],
          annotations: [{ square: 'e5', text: '唯一炮架' }, { square: 'e2', text: '第二个棋子' }]
        }
      ],
      code: `// 逐格规则本体：当前已搬到 init_attack_tables
nr = sr + d;
while (inside(nr) && !occupied(nr)) {
  moves |= 1 << nr; nr += d;       // 炮架前可空走
}
if (inside(nr)) {                   // 找到炮架
  nr += d;
  while (inside(nr) && !occupied(nr)) nr += d;
  if (inside(nr)) moves |= 1 << nr; // 第二个子可吃
}`,
      steps: ['从源点向两个方向逐格检查', '炮架前的空格可以落子', '遇到第一枚棋子后继续找，第二枚才是吃子目标', '当前源码仍使用这段规则，但只在启动建表时执行'],
      notes: '先看不查表时怎样回答一条炮路。红炮从第七行向上，先看第六行，再在第五行遇到炮架；越过后继续看第四、第三、第二行，才找到可吃的黑车。向下还要独立扫描。【按键】屏幕上的 inside 和 occupied 是便于阅读的简写；源码实际用边界判断和 `(occ >> nr) & 1` 读取占位位。重要的是，这不是当前搜索期每次生成走法的现状：当前实现已把同样的逐格循环搬进 `init_attack_tables`，启动时预先算好。下一页先看为什么值得这样做。',
      sources: ['象棋教学局面核验.md:C', 'xiangqi_ai.cpp:228-246', 'xiangqi_ai.cpp:258-273'],
      takeaway: '不预计算时，一次直线查询要现场找到第一、第二个阻挡。'
    },
    {
      id: 'a18b',
      title: '真正的成本：搜索反复询问车炮线路',
      eyebrow: '热点不在十格，而在重复次数',
      layout: 'cards',
      lead: '一次扫描很短；搜索树中的走法生成、静止搜索和合法性检查会不断重复它。',
      cards: [
        { title: '主搜索', text: '每个展开的局面调用 gen_all_moves，再逐子调用 gen_moves_for。' },
        { title: 'QS', text: '叶子处的静止搜索仍会生成应将或吃子候选。' },
        { title: '试走过滤', text: '每试走一个候选，is_in_check 还要查将位所在的一行一列。' },
        { title: '重复单位', text: '棋种 + 源点在线上的位置 + 当前 9/10-bit 占位。' }
      ],
      code: `minimax 局面
  └─ gen_all_moves(...)          // 主搜索 / QS
      └─ gen_moves_for(...)      // 每枚本方棋子

每试走一个候选
  └─ make_move → is_in_check     // 再查直线攻击`,
      steps: ['主搜索在展开局面时生成全部候选', 'QS 在普通深度用完后仍生成战术候选', '每个候选试走后，合法性检查还会查车炮攻击', '若线长为 L、输出 k 个着，逐格方案是 O(L)+O(k)'],
      notes: '一条线最多只有十个交叉点，单次扫描并不惊人。但搜索在每个展开的局面都会调用 `gen_all_moves`，它再遍历本方棋子并调用 `gen_moves_for`。普通深度用完后，QS 还会生成吃子或应将候选。【按键】而且每个候选试走后，`is_in_check` 要从将位反向检查同行、同列的车炮。因此真正的重复单位是“棋种、源点在线上的位置、当前占位”这个查询；不是说每个搜索节点的局面都一样。若把线长记为 L，现场找阻挡需要 O(L)，再输出 k 个走法需要 O(k)。对固定 9×10 棋盘，它们渐进上都可以看作常数；这里节省的是搜索热点中反复边界判断、读占位和分支的常数成本。',
      sources: ['xiangqi_ai.cpp:772-824', 'xiangqi_ai.cpp:1047-1073', 'xiangqi_ai.cpp:1123-1129', 'xiangqi_ai.cpp:1249-1250', 'xiangqi_ai.cpp:1371-1383'],
      takeaway: '慢不在一条线最多十格，而在搜索把这种查询调用了很多次。'
    },
    {
      id: 'a18c',
      title: '把扫描搬到启动期，搜索期直接查表',
      eyebrow: '建表 → 增量维护 → 查询输出',
      layout: 'compare',
      lead: '所有占位模式只预计算一次；走棋只翻起终点的 bit，之后用整数占位选中表项。',
      cards: [
        { title: '① 启动建表', text: '行：9×512 种输入；列：10×1024 种输入。车、炮分别保存攻击 mask。' },
        { title: '② 走棋 / 悔棋', text: 'row_occ 与 col_occ 只更新起点、终点；side_* 同步记录双方占位。' },
        { title: '③ 搜索查询', text: 'TABLE[source][occ] 取回整条线，位运算滤掉己子，再只枚举置位。' }
      ],
      code: `// 启动：枚举源行与全部 10-bit 占位
for (int sr=0; sr<10; ++sr) for (int occ=0; occ<1024; ++occ)
  CANNON_COL_ATT[sr][occ] = precompute(sr, occ);

// make / undo：对称地翻起终点 bit
col_occ[c2] |= 1 << r2;  col_occ[c1] &= ~(1 << r1);

// 搜索：查表、滤己子、逐个输出置位
att = CANNON_COL_ATT[r][col_occ[c]] & ~side_col_occ[side][c];
while (att) { nr=__builtin_ctz(att); att&=att-1; ADDM(r,c,nr,c); }`,
      table: {
        headers: ['本例的列查询', '整数 / 置位', '含义'],
        rows: [
          ['col_occ[4]', '676 = {2,5,7,9}', '黑车、炮架、红炮、红帅占位'],
          ['CANNON_COL_ATT[7][676]', '324 = {2,6,8}', '(2,4) 可吃；(6,4)、(8,4) 可空走'],
          ['过滤己子后', '{2,6,8}', '本例三个目标都保留']
        ]
      },
      steps: ['启动时枚举源位与所有占位，用逐格规则写入四张表', '棋盘初始化和 make/undo 持续维护行列占位', '搜索期一次数组索引得到攻击 mask，再过滤己子', 'ctz 取最低置位，mask&=mask-1 删除它，直到输出全部 k 个着'],
      notes: '现在把三段接起来。程序启动时，`init_attack_tables` 枚举源位置和该线的全部占位整数：一行有九位、五百一十二种，一列有十位、一千零二十四种。它用前一页的逐格规则算出车、炮攻击 mask，写入四张表。【按键】搜索期不重新扫整盘：`make_move` 和 `undo_move` 只修改起点、终点对应的 `row_occ`、`col_occ` 以及双方占位。吃子时目标格仍有子，所以总占位保持为一，只更换阵营占位。【按键】回到这盘：第四列在第二、五、七、九行有子，因此 `col_occ[4]=676`。用源行七查 `CANNON_COL_ATT[7][676]`，得到 324，也就是置位二、六、八：二是越过第五行炮架后的吃子目标，六和八是炮架前的空走格。随后用阵营占位滤掉己子，`ctz` 取出一个置位，`att &= att-1` 删除它，直到生成全部走法。查表是 O(1)，输出 k 个走法仍是 O(k)。四张 `uint16_t` 表约占 58 KiB，make/undo 增加常数次位运算。项目没有 RankMask 前后对照测速，因此不声称具体加速倍数。工程优化讲完以后，最后回放整条推演链，收束规则、评价与搜索。',
      sources: ['xiangqi_ai.cpp:210-279', 'xiangqi_ai.cpp:316-320', 'xiangqi_ai.cpp:444-473', 'xiangqi_ai.cpp:485-604', 'xiangqi_ai.cpp:669-711', 'xiangqi_ai.cpp:1612-1616'],
      takeaway: '搜索不再现场找阻挡：占位整数直接选中预先算好的攻击 mask。'
    },
    {
      id: 'a21b',
      title: '它为什么这样选择？',
      eyebrow: '整条推演链回放',
      layout: 'cards',
      lead: '答案来自一条在有限时间内不断修正判断的完整链路。',
      cards: [
        { title: '1 · 生成', text: '按象棋走法生成候选，试走后过滤送将。' },
        { title: '2 · 排序', text: 'TT、吃子、killer、counter、history 猜谁更值得先看。' },
        { title: '3 · 推演', text: '双方轮流选择；Alpha-Beta 与 PVS 建立并挑战边界。' },
        { title: '4 · 稳定叶子', text: 'QS、SEE 与有限将军延伸处理未结束的战斗。' },
        { title: '5 · 分配预算', text: '选择性搜索少看或跳过；同时标记它带来的漏棋风险。' },
        { title: '6 · 按时交卷', text: '返回最后一个完整迭代的最佳着。' }
      ],
      steps: ['规则先决定哪些候选值得进入搜索', '排序让更可能的好着先建立边界', '评分指导搜索，具体应手又修正静态偏好', '选择性搜索集中预算，同时承担明确的漏棋风险', '时间到，返回最后一个完整迭代的答案'],
      notes: '现在再回答“它为什么这样选择”。候选首先必须合法；排序猜谁更值得先看；评分给搜索叶子一种棋感，例如 PST 可以表达兵在某些位置蓄势的偏好，但能不能安全推进、什么时候进底线参与做杀，要让搜索展开对手应手来检验。评估指导搜索，搜索又用具体变化修正静态偏好。QS、有限深度和启发式裁剪决定了程序实际能看到的范围。时间到时，它返回上一轮完整结果，避开半截深搜里的偶然高分。接下来回到开场的三个阶段，看看这套系统怎样合在一起。',
      sources: ['xiangqi_ai.cpp:669-790', 'xiangqi_ai.cpp:791-1118', 'xiangqi_ai.cpp:1123-1542', 'xiangqi_ai.cpp:1545-1605'],
      takeaway: '一次落子是规则、记忆、评估和搜索共同作用的结果。'
    },
    {
      id: 'a22',
      title: '从“什么都不会”到一台会思考的象棋系统',
      eyebrow: '回到开场的三个阶段',
      layout: 'map',
      currentChapter: 2,
      lead: '每个实际问题，都推动系统补上一种能力。',
      steps: ['会走：生成符合棋子规则的候选，试走后排除送将', '会评价：把子力与位置变成可比较的静态信号', '会搜索：考虑对手，用缓存、边界与启发式分配时间'],
      notes: '回到开场，搭建过程走过三个阶段。第一，电脑学会表示棋盘、生成候选，并用试走与查将留下合法着。第二，静态评估把子力与位置变成可比较的信号，让候选有了方向。第三，搜索展开双方应手，用 Alpha-Beta 建立边界，用 Zobrist 和置换表复用算过的局面，再用排序、减深和剪枝把时间集中到更值得看的路线。规则决定能不能走，评价提供方向，搜索负责检验与选择；这些能力在当前引擎里相互配合，也相互制约。【停顿】现在回看最初的问题：“电脑计算快，能不能帮我下棋？”我们真正需要的是一套把棋盘、判断、搜索记忆和时间组织起来的系统。',
      sources: ['xiangqi_ai.cpp'],
      takeaway: '象棋引擎把规则、记忆、评估和搜索组织成一套协作系统。'
    }
  ]
});
