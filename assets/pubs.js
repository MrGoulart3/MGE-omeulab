(function(){
  var root=document.documentElement;
  // marcações de pendência
  var tp=document.getElementById('togglepend');if(tp)tp.addEventListener('click',function(){root.classList.toggle('nopend')});
  // publicações
  var P=JSON.parse(document.getElementById('publicacoes-data').textContent);
  var ol=document.getElementById('pubs');
  var items=ol.querySelectorAll('.pub');
  P.forEach(function(p,i){if(items[i])items[i].dataset.k=p.k});
  document.querySelectorAll('[data-f]').forEach(function(b){b.addEventListener('click',function(){
    document.querySelectorAll('[data-f]').forEach(function(x){x.setAttribute('aria-pressed',String(x===b))});
    ol.querySelectorAll('.pub').forEach(function(li){li.hidden=!(b.dataset.f==='all'||li.dataset.k===b.dataset.f)})})});
  // copiar e-mail
  document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){
    var t=b.dataset.copy;var ok=function(){b.textContent='✓';b.setAttribute('aria-label',root.dataset.lang==='en'?'Email copied':'E-mail copiado')};
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(ok,function(){sel()})}else sel();
    function sel(){var r=document.createRange();r.selectNodeContents(document.getElementById('mail'));var s=getSelection();s.removeAllRanges();s.addRange(r)}
  })});
})();
