(function () {
  const FILES = 'abcdefghi';
  const GLYPHS = { K:'帅', A:'仕', B:'相', N:'马', R:'车', C:'炮', P:'兵', k:'将', a:'士', b:'象', n:'马', r:'车', c:'炮', p:'卒' };

  function parseSquare(square) {
    if (Array.isArray(square)) return { file: square[0], rank: square[1] };
    const m = /^([a-i])(\d)$/.exec(square);
    if (!m) throw new Error(`无效象棋坐标: ${square}`);
    return { file: FILES.indexOf(m[1]), rank: Number(m[2]) };
  }

  function parseFen(fen) {
    if (!fen) return [];
    const rows = fen.trim().split(/\s+/)[0].split('/');
    if (rows.length !== 10) throw new Error('象棋 FEN 必须包含 10 行');
    return rows.flatMap((row, rank) => {
      let file = 0, pieces = [];
      for (const token of row) {
        if (/\d/.test(token)) file += Number(token);
        else { pieces.push({ type: token, square: `${FILES[file]}${rank}` }); file += 1; }
      }
      if (file !== 9) throw new Error(`FEN 第 ${rank + 1} 行不是 9 路`);
      return pieces;
    });
  }

  function point(square, orientation, size) {
    const { file, rank } = parseSquare(square);
    if (file < 0 || file > 8 || rank < 0 || rank > 9) throw new Error(`坐标越界: ${square}`);
    const shownFile = orientation === 'black' ? 8 - file : file;
    const shownRank = orientation === 'black' ? 9 - rank : rank;
    return { x: size.margin + shownFile * size.cell, y: size.margin + shownRank * size.cell };
  }

  function line(x1,y1,x2,y2,cls='board-line') { return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="${cls}"/>`; }
  function escapeText(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  function render(target, options = {}) {
    const el = typeof target === 'string' ? document.querySelector(target) : target;
    const size = { margin: 34, cell: options.cell || 46 };
    const width = size.margin * 2 + size.cell * 8;
    const height = size.margin * 2 + size.cell * 9;
    const orientation = options.orientation || 'red';
    const pieces = options.fen ? parseFen(options.fen) : (options.pieces || []);
    const coordinateLabel = `坐标采用(行,列)0-based；${orientation==='black'?'黑方':'红方'}视角`;
    let svg = `<svg class="xq-board ${options.heatmap?.length?'heatmap-mode':''}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeText(`${options.label || '象棋棋盘'}，${coordinateLabel}`)}"><defs><marker id="arrow-${el.id}" markerWidth="6" markerHeight="6" refX="5" refY="2.5" orient="auto"><path d="M0,0 L0,5 L6,2.5 z"/></marker></defs><rect class="board-paper" x="1" y="1" width="${width-2}" height="${height-2}" rx="5"/>`;
    svg += `<text x="5" y="13" class="axis-title">行</text><text x="${width-14}" y="13" class="axis-title">列</text>`;
    for (let shownFile=0;shownFile<9;shownFile++) {
      const column=orientation==='black'?8-shownFile:shownFile;
      svg += `<text x="${size.margin+shownFile*size.cell}" y="13" class="axis-label axis-column" data-axis="column">${column}</text>`;
    }
    for (let shownRank=0;shownRank<10;shownRank++) {
      const row=orientation==='black'?9-shownRank:shownRank;
      svg += `<text x="13" y="${size.margin+shownRank*size.cell+4}" class="axis-label axis-row" data-axis="row">${row}</text>`;
    }
    for (let r=0;r<10;r++) svg += line(size.margin,size.margin+r*size.cell,width-size.margin,size.margin+r*size.cell);
    for (let f=0;f<9;f++) {
      const x=size.margin+f*size.cell;
      if (f===0||f===8) svg += line(x,size.margin,x,height-size.margin);
      else { svg += line(x,size.margin,x,size.margin+4*size.cell); svg += line(x,size.margin+5*size.cell,x,height-size.margin); }
    }
    [[3,0,5,2],[5,0,3,2],[3,7,5,9],[5,7,3,9]].forEach(([a,b,c,d])=>svg+=line(size.margin+a*size.cell,size.margin+b*size.cell,size.margin+c*size.cell,size.margin+d*size.cell));
    svg += `<text x="${width*.27}" y="${size.margin+4.62*size.cell}" class="river-text">楚河</text><text x="${width*.67}" y="${size.margin+4.62*size.cell}" class="river-text">汉界</text>`;
    (options.heatmap || []).forEach(h => { const p=point(h.square,orientation,size); const v=Math.max(0,Math.min(1,h.value/(options.heatMax||100))); svg += `<circle cx="${p.x}" cy="${p.y}" r="${size.cell*.42}" class="heat" style="--heat:${v}"/><text x="${p.x}" y="${p.y+5}" class="heat-value">${h.value}</text>`; });
    (options.highlights || []).forEach(h => { const p=point(h.square,orientation,size); const frag=h.fragmentIndex==null?'':` fragment" data-fragment-index="${h.fragmentIndex}`; svg += `<circle cx="${p.x}" cy="${p.y}" r="${size.cell*.43}" class="highlight ${h.kind||''}${frag}"/>`; });
    (options.arrows || []).forEach(a => { const p1=point(a.from,orientation,size), p2=point(a.to,orientation,size), dx=a.offsetX||0, dy=a.offsetY||0; const frag=a.fragmentIndex==null?'':` fragment" data-fragment-index="${a.fragmentIndex}`; svg += `<line x1="${p1.x+dx}" y1="${p1.y+dy}" x2="${p2.x+dx}" y2="${p2.y+dy}" class="move-arrow ${a.kind||''}${frag}" marker-end="url(#arrow-${el.id})"/>`; });
    pieces.forEach(piece => { const p=point(piece.square,orientation,size); const red=piece.type===piece.type.toUpperCase(); const frag=piece.fragmentIndex==null?'':` fragment" data-fragment-index="${piece.fragmentIndex}`; svg += `<g class="piece ${red?'red':'black'}${frag}" transform="translate(${p.x} ${p.y})"><circle r="${size.cell*.36}"/><text y="7">${GLYPHS[piece.type]||piece.type}</text></g>`; });
    (options.annotations || []).forEach(a => { const p=point(a.square,orientation,size), dx=a.dx==null?18:a.dx, dy=a.dy==null?-22:a.dy; svg += `<g class="annotation ${a.kind||''}" transform="translate(${p.x+dx} ${p.y+dy})"><rect x="-4" y="-17" width="${String(a.text).length*14+12}" height="23" rx="5"/><text y="0">${escapeText(a.text)}</text></g>`; });
    svg += '</svg>';
    el.innerHTML = svg;
    return el.querySelector('svg');
  }

  window.XiangqiBoard = { render, parseFen, parseSquare, point };
})();
