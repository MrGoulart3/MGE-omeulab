/* Dipirona 3D. O 3Dmol.js (WebGL; esferas e bastões sombreados, cores Jmol) é carregado sem bloquear a página,
   com SRI; o contêiner #molview mantém o aspect-ratio enquanto isso. Gira sempre (pedido do Mario), pausa só fora da
   tela e volta a girar depois de arrastar. Se o 3Dmol não carregar ou o WebGL falhar, usa o renderizador próprio em canvas. */
(function(){
  var el=document.getElementById('molview'); if(!el)return;
  var A=JSON.parse(document.getElementById('dipirona-data').textContent);
  function init3d(){
    var xyz=A.length+'\ndipirona\n'+A.map(function(a){return a[0]+' '+a[1]+' '+a[2]+' '+a[3]}).join('\n');
  try{
    var v=$3Dmol.createViewer(el,{backgroundColor:'white',backgroundAlpha:0,antialias:true});
    if(!v)return false;
    v.addModel(xyz,'xyz');
    v.setStyle({},{stick:{radius:0.15,colorscheme:'Jmol'},sphere:{scale:0.25,colorscheme:'Jmol'}});
    v.zoomTo(); v.zoom(1.15); v.render();
    /* gira sempre (pedido do Mario); pausa só fora da tela e volta a girar depois de arrastar */
    var gira=function(on){try{v.spin(on?'y':false,0.8)}catch(_){}};
    gira(true); setTimeout(function(){gira(true)},400);
    if('IntersectionObserver' in window)new IntersectionObserver(function(e){gira(e[0].isIntersecting)}).observe(el);
    ['pointerup','touchend','mouseup'].forEach(function(n){el.addEventListener(n,function(){setTimeout(function(){gira(true)},600)})});
    addEventListener('resize',function(){v.resize();v.render()});
    window.__mol3dmol=v;
    return true;
  }catch(e){window.__mol3dmol=null;return false}
  }
  /* renderizador próprio em canvas (sem bibliotecas): esferas sombreadas, ligações por distância,
     ordem de pintura por profundidade, rotação automática, arraste para girar, pausa fora da tela */
  function canvasFallback(){
  var cv=document.getElementById('mol3d'); if(!cv||!cv.getContext)return;
  cv.hidden=false; var mv=document.getElementById('molview'); if(mv)mv.hidden=true;
  var R={H:0.31,C:0.76,N:0.71,O:0.66,S:1.05}, VIS={H:0.25,C:0.38,N:0.37,O:0.36,S:0.50};
  var cx=0,cy=0,cz=0; A.forEach(function(a){cx+=a[1];cy+=a[2];cz+=a[3]}); cx/=A.length;cy/=A.length;cz/=A.length;
  var P=A.map(function(a){return {e:a[0],x:a[1]-cx,y:a[2]-cy,z:a[3]-cz}});
  var B=[]; for(var i=0;i<P.length;i++)for(var j=i+1;j<P.length;j++){var d=Math.hypot(P[i].x-P[j].x,P[i].y-P[j].y,P[i].z-P[j].z);
    if(d<1.18*(R[P[i].e]+R[P[j].e]))B.push([i,j]);}
  var ext=0; P.forEach(function(p){ext=Math.max(ext,Math.hypot(p.x,p.y,p.z))});
  var ctx=cv.getContext('2d'), dpr=Math.min(window.devicePixelRatio||1,2);
  function size(){var w=cv.clientWidth||cv.parentNode.clientWidth||520,h=w*420/520;cv.width=w*dpr;cv.height=h*dpr}
  size(); addEventListener('resize',function(){size();draw()});
  function col(e){return getComputedStyle(document.documentElement).getPropertyValue('--at-'+e).trim()||'#888'}
  var C={}; function cols(){['H','C','N','O','S'].forEach(function(e){C[e]=col(e)});C.bond=getComputedStyle(document.documentElement).getPropertyValue('--ink2').trim()}
  cols(); if(window.matchMedia)matchMedia('(prefers-color-scheme: dark)').addEventListener('change',cols);
  new MutationObserver(cols).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  var ry=0.6, rx=-0.35, auto=true, vis=true, drag=null;
  function shade(hex,k){var n=parseInt(hex.replace('#',''),16),r=n>>16,g=n>>8&255,b=n&255;
    function f(c){return Math.max(0,Math.min(255,Math.round(k>0?c+(255-c)*k:c*(1+k))))}return 'rgb('+f(r)+','+f(g)+','+f(b)+')'}
  function draw(){
    var W=cv.width,H=cv.height,s=Math.min(W,H)/(1.75*ext+0.6), cyw=Math.cos(ry),syw=Math.sin(ry),cxw=Math.cos(rx),sxw=Math.sin(rx);
    var Q=P.map(function(p){var x=p.x*cyw+p.z*syw, z=-p.x*syw+p.z*cyw, y=p.y*cxw-z*sxw; z=p.y*sxw+z*cxw;
      var f=1+z*0.04; return {e:p.e,X:W/2+x*s*f,Y:H/2-y*s*f,z:z,r:VIS[p.e]*s*f}});
    ctx.clearRect(0,0,W,H);
    var items=[]; Q.forEach(function(q,i){items.push({z:q.z,t:0,i:i})});
    B.forEach(function(b){items.push({z:(Q[b[0]].z+Q[b[1]].z)/2-0.01,t:1,b:b})});
    items.sort(function(a,b){return a.z-b.z});
    items.forEach(function(it){
      if(it.t===1){var a=Q[it.b[0]],c=Q[it.b[1]],dx=c.X-a.X,dy=c.Y-a.Y,L=Math.hypot(dx,dy)||1,ux=dx/L,uy=dy/L;
        /* bastão começa e termina na borda das esferas (não entra nelas) */
        var ax=a.X+ux*a.r*0.82,ay=a.Y+uy*a.r*0.82,cx2=c.X-ux*c.r*0.82,cy2=c.Y-uy*c.r*0.82,mx=(ax+cx2)/2,my=(ay+cy2)/2;
        if(L<(a.r+c.r)*0.82)return;
        ctx.lineCap='butt';ctx.lineWidth=Math.max(2,0.13*s);
        ctx.strokeStyle=shade(C[a.e],-0.1);ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(mx,my);ctx.stroke();
        ctx.strokeStyle=shade(C[c.e],-0.1);ctx.beginPath();ctx.moveTo(mx,my);ctx.lineTo(cx2,cy2);ctx.stroke();return}
      var q=Q[it.i],g=ctx.createRadialGradient(q.X-q.r*0.35,q.Y-q.r*0.4,q.r*0.1,q.X,q.Y,q.r);
      g.addColorStop(0,shade(C[q.e],0.55));g.addColorStop(0.55,C[q.e]);g.addColorStop(1,shade(C[q.e],-0.45));
      ctx.fillStyle=g;ctx.beginPath();ctx.arc(q.X,q.Y,q.r,0,6.2832);ctx.fill()});
  }
  draw(); var last=0; function loop(t){ if(vis&&auto&&!drag&&!document.hidden){ry+=(t-last)/1000*0.45} last=t; draw(); requestAnimationFrame(loop)}
  requestAnimationFrame(function(t){last=t;loop(t)});
  if('IntersectionObserver' in window)new IntersectionObserver(function(e){vis=e[0].isIntersecting}).observe(cv);
  cv.addEventListener('pointerdown',function(e){drag={x:e.clientX,y:e.clientY};cv.setPointerCapture(e.pointerId)});
  cv.addEventListener('pointermove',function(e){if(!drag)return;ry+=(e.clientX-drag.x)*0.01;rx=Math.max(-1.4,Math.min(1.4,rx+(e.clientY-drag.y)*0.01));drag={x:e.clientX,y:e.clientY}});
  ['pointerup','pointercancel'].forEach(function(n){cv.addEventListener(n,function(){drag=null})});
  }
  function fallback(){ if(!window.__mol3dmol) canvasFallback(); }
  function ready(){ if(!(window.$3Dmol&&init3d())) fallback(); }
  if(window.$3Dmol){ ready(); return; }
  var s=document.createElement('script');
  s.src='https://cdn.jsdelivr.net/npm/3dmol@2.5.5/build/3Dmol-min.js';
  s.integrity='sha384-OsczYbldvrHgslr9fFp/i4GiLSeuw9l+QIlv99ITw8soOwXcoGeflFMLg+CU/X1d';
  s.crossOrigin='anonymous'; s.async=true;
  s.onload=ready; s.onerror=fallback;
  document.head.appendChild(s);
})();
