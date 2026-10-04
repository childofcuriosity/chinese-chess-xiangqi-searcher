(function () {
  const exporting = new URLSearchParams(location.search).has('export-pdf');
  if (exporting) document.documentElement.classList.add('pdf-export');
  // Measure each slide at its natural width; reduce its type only as needed.
  async function fitSlides() {
    await document.fonts.ready;
    await Promise.all([...document.images].map(img => img.complete ? Promise.resolve() : new Promise(resolve => {img.onload=resolve;img.onerror=resolve;})));
    const slides = [...document.querySelectorAll('#slides > section')];
    for (const [i, slide] of slides.entries()) {
      const previous = slide.getAttribute('style') || '';
      if (!exporting) slide.style.cssText = 'display:block;position:relative;transform:none;visibility:hidden;width:1280px;height:auto;top:0;left:0;';
      let size=36;
      for (;size>=23;size-=.5) {
        slide.style.fontSize=size+'px';
        const children=[...slide.children].filter(x=>!x.matches('aside.notes,.pdf-page-number'));
        const bounds=slide.getBoundingClientRect();
        const bottom=Math.max(...children.map(x=>x.getBoundingClientRect().bottom-bounds.top));
        if(bottom<=665)break;
      }
      slide.setAttribute('style',previous);
      slide.style.fontSize=size+'px';
      if(exporting){const n=document.createElement('div');n.className='pdf-page-number';n.textContent=`${i+1} / ${slides.length}`;slide.appendChild(n);}
    }
    Reveal.layout();
    document.documentElement.dataset.slidesReady='true';
  }
  if(Reveal.isReady())fitSlides(); else Reveal.on('ready',fitSlides);
})();
