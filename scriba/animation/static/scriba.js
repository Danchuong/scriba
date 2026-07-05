// scriba.js — Scriba animation runtime (external asset)
// Loaded via <script src="scriba.<hash>.js" defer> for CSP-strict deployments.
// Zero per-render variability — fully cacheable and SRI-hashable.
(function(){
  // Theme toggle: delegated from data-scriba-action="theme-toggle".
  // Sliced verbatim into standalone pages by _script_builder
  // (_theme_toggle_script) — render.py used to hand-maintain a third
  // copy of this listener; one source now, like the CORE slice.
  // __SCRIBA_THEME_START__
  document.addEventListener('click',function(e){
    var btn=e.target.closest('[data-scriba-action="theme-toggle"]');
    if(btn){
      var t=document.documentElement.dataset.theme;
      document.documentElement.dataset.theme=(t==='dark'?'light':'dark');
    }
  });
  // __SCRIBA_THEME_END__

  // Everything between the CORE sentinels is the per-widget state machine.
  // _script_builder._build_inline_script slices this region verbatim into
  // the inline <script> (binding its own W/frames), so the inline runtime
  // is DERIVED from this file — never authored separately. Keep the region
  // self-contained: no references to module-scope state.
  function _scribaInit(W,frames){
  // __SCRIBA_CORE_START__
    var _cssEscape=(typeof CSS!=='undefined'&&CSS.escape)?CSS.escape:function(s){return String(s).replace(/[^a-zA-Z0-9_-]/g,function(c){return '\\'+c.charCodeAt(0).toString(16)+' ';});};
    var cur=0;
    var stage=W.querySelector('.scriba-stage');
    var narr=W.querySelector('.scriba-narration');
    var subC=W.querySelector('.scriba-substory-container');
    var ctr=W.querySelector('.scriba-step-counter');
    var prev=W.querySelector('.scriba-btn-prev');
    var next=W.querySelector('.scriba-btn-next');
    var dots=W.querySelectorAll('.scriba-dot');
    var _anims=[];
    var _animState='idle';
    // Transition generation: bumped on every supersede (_cancelAnims).
    // Orphaned async callbacks (setTimeout/Promise) captured under an older
    // generation self-abort instead of mutating the superseding frame.
    var _gen=0;
    var _motionMQ=window.matchMedia('(prefers-reduced-motion:reduce)');
    var _canAnim=(typeof Element.prototype.animate==='function')&&!_motionMQ.matches;
    (function(){var _mh=function(ev){_canAnim=(typeof Element.prototype.animate==='function')&&!ev.matches;};if(_motionMQ.addEventListener){_motionMQ.addEventListener('change',_mh);}else if(_motionMQ.addListener){_motionMQ.addListener(function(mq){_mh({matches:mq.matches});});}})();
    var DUR=180;          // ms — primary WAAPI transition baseline
    // DUR_PATH_DRAW is intentionally shorter than DUR: drawn annotations feel snappier
    // than discrete element adds because the stroke-draw motion already implies "appearing".
    // Unifying to DUR would make path draws feel sluggish. Keep distinct.
    var DUR_PATH_DRAW=120; // ms — annotation path stroke-draw
    var DUR_VALUE=100;     // ms — value-change scale bounce (snappier than baseline)
    var DUR_ARROWHEAD=36;  // ms — arrowhead/label fade after path draw (~2 frames @ 60fps)
    var DUR_STAGGER=50;    // ms — phase-1 → phase-2 gap (annotation/highlight before moves)
    var DUR_SYNC_FUDGE=20; // ms — extra margin for needsSync timeout beyond _dur(DUR)
    var DUR_EMPH=700;      // ms — delta-emphasis class dwell; the pulse itself lives in CSS .scriba-emphasis
    var EMPH_CAP=8;        // max changed targets to pulse on arrival; above this the snap alone carries
    var _speed=parseFloat(W.getAttribute('data-scriba-speed'))||1;
    function _dur(ms){return Math.round(ms/_speed);}
    function _cancelAnims(){
      _gen++;
      for(var k=0;k<_anims.length;k++)try{_anims[k].finish();}catch(e){}
      _anims=[];_animState='idle';
    }
    function initSub(el){
      var fd=JSON.parse(el.getAttribute('data-scriba-frames'));
      var sc=0,ss=el.querySelector('.scriba-stage'),sn=el.querySelector('.scriba-narration');
      var sp=el.querySelector('.scriba-btn-prev'),sx=el.querySelector('.scriba-btn-next');
      var sr=el.querySelector('.scriba-step-counter'),sd=el.querySelectorAll('.scriba-dot');
      function sh(i){sc=i;ss.innerHTML=fd[i].svg;sn.innerHTML=fd[i].narration;
        sr.textContent=(i+1)+' / '+fd.length;
        sp.disabled=i===0;sx.disabled=i===fd.length-1;
        sd.forEach(function(d,j){d.className='scriba-dot'+(j===i?' active':j<i?' done':'');});
      }
      sp.addEventListener('click',function(){if(sc>0)sh(sc-1);});
      sx.addEventListener('click',function(){if(sc<fd.length-1)sh(sc+1);});
      sh(0);
    }
    function _updateControls(i){
      ctr.textContent=(i+1)+' / '+frames.length;
      prev.disabled=i===0;
      next.disabled=i===frames.length-1;
      dots.forEach(function(d,j){d.className='scriba-dot'+(j===i?' active':j<i?' done':'');});
    }
    function _annKeysIn(svgStr){
      var keys={};
      if(!svgStr)return keys;
      var re=/data-annotation="([^"]*)"/g,m;
      while((m=re.exec(svgStr))!==null){keys[m[1]]=true;}
      return keys;
    }
    function _fadeInNewAnnotations(prevKeys){
      if(!_canAnim)return;
      var els=stage.querySelectorAll('[data-annotation]');
      for(var k=0;k<els.length;k++){
        var key=els[k].getAttribute('data-annotation');
        if(prevKeys[key])continue;
        var a=els[k].animate([{opacity:0},{opacity:1}],
          {duration:_dur(DUR),easing:'cubic-bezier(0.16,1,0.3,1)',fill:'forwards'});
        _anims.push(a);
      }
    }
    function snapToFrame(i){
      _cancelAnims();
      var prevKeys=_annKeysIn(frames[cur]&&frames[cur].svg);
      cur=i;
      stage.innerHTML=frames[i].svg;
      narr.innerHTML=frames[i].narration;
      subC.innerHTML=frames[i].substory||'';
      subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
      _updateControls(i);
      _fadeInNewAnnotations(prevKeys);
    }
    function _arrowheadAt(path,size){
      var len=path.getTotalLength();
      var tip=path.getPointAtLength(len);
      var back=path.getPointAtLength(Math.max(0,len-size*1.5));
      var dx=tip.x-back.x,dy=tip.y-back.y;
      var d=Math.sqrt(dx*dx+dy*dy)||1;
      var ux=dx/d,uy=dy/d,px=-uy,py=ux;
      var hw=size*0.5;
      return tip.x+','+tip.y+' '+(tip.x-ux*size+px*hw)+','+(tip.y-uy*size+py*hw)+' '+(tip.x-ux*size-px*hw)+','+(tip.y-uy*size-py*hw);
    }
    function _annEl(root,target){
      // The differ composites a position-only pill as "{base}-solo", but the
      // SVG emitter keys it "{base}-position-{above|below|left|right}", so the
      // direct match misses. Recover the base and try the four sides before
      // giving up. Harmless when the direct key already matches (first hit wins).
      var el=root.querySelector('[data-annotation="'+_cssEscape(target)+'"]');
      if(el)return el;
      var base=target.replace(/-solo$/,'');
      if(base!==target){
        var sides=['above','below','left','right'];
        for(var i=0;i<sides.length;i++){
          el=root.querySelector('[data-annotation="'+_cssEscape(base+'-position-'+sides[i])+'"]');
          if(el)return el;
        }
      }
      return null;
    }
    function _applyTransition(rec,parsed,pending){
      var target=rec[0],prop=rec[1],fromVal=rec[2],toVal=rec[3],kind=rec[4];
      var sel='[data-target="'+_cssEscape(target)+'"]';
      if(kind==='recolor'){
        var el=stage.querySelector(sel);
        if(el){
          var cls=el.className.baseVal||el.className||'';
          cls=cls.replace('scriba-state-'+fromVal,'scriba-state-'+toVal);
          if(el.className.baseVal!==undefined)el.className.baseVal=cls;
          else el.className=cls;
        }
      }else if(kind==='value_change'){
        var el2=stage.querySelector(sel);
        if(el2){var txt=el2.querySelector('text');
          // math values ($...$) render as KaTeX foreignObject in the next
          // frame's server SVG — writing the raw string into <text> here
          // would flash "$\max(0,i)$" mid-transition; pulse only instead
          // toVal!=null: inverting a value_change whose from was null yields a
          // null target — pulse only, never stamp the literal "null" into <text>.
          if(txt&&toVal!=null&&String(toVal).indexOf('$')===-1){txt.textContent=toVal;}
          var vt=txt||el2.querySelector('foreignObject > div');
          if(vt&&_canAnim){vt.animate([{transform:'scale(1)'},{transform:'scale(1.15)'},{transform:'scale(1)'}],
            {duration:_dur(DUR_VALUE),easing:'ease-out'});}
        }
      }else if(kind==='highlight_on'){
        var el3=stage.querySelector(sel);
        if(el3){
          var c3=el3.className.baseVal||el3.className||'';
          if(c3.indexOf('scriba-highlighted')===-1){
            c3+=' scriba-highlighted';
            if(el3.className.baseVal!==undefined)el3.className.baseVal=c3;
            else el3.className=c3;
          }
        }
      }else if(kind==='highlight_off'){
        var el4=stage.querySelector(sel);
        if(el4){
          var c4=el4.className.baseVal||el4.className||'';
          c4=c4.replace(/\s*scriba-highlighted/g,'');
          if(el4.className.baseVal!==undefined)el4.className.baseVal=c4;
          else el4.className=c4;
        }
      }else if(kind==='element_remove'){
        var el5=stage.querySelector(sel);
        if(el5){
          var a5=el5.animate([{opacity:1},{opacity:0}],
            {duration:_dur(DUR),easing:'ease-in',fill:'forwards'}); // fade-out accelerates → ease-in
          _anims.push(a5);pending.push(a5.finished);
        }
      }else if(kind==='element_add'){
        var src=parsed.querySelector(sel);
        if(src){
          var clone=document.adoptNode(src.cloneNode(true));
          clone.style.opacity='0';
          var srcP=src.parentNode;
          var pShape=null;
          while(srcP&&srcP.nodeType===1){
            var ds2=srcP.getAttribute&&srcP.getAttribute('data-shape');
            if(ds2){pShape=stage.querySelector('[data-shape="'+_cssEscape(ds2)+'"]');break;}
            srcP=srcP.parentNode;
          }
          var ct=pShape||stage.querySelector('svg');
          if(ct){ct.appendChild(clone);
            var a6=clone.animate([{opacity:0},{opacity:1}],
              {duration:_dur(DUR),easing:'ease-out',fill:'forwards'}); // fade-in decelerates → ease-out
            _anims.push(a6);pending.push(a6.finished);
          }
        }
      }else if(kind==='position_move'){
        // An identity-keyed cell/node slides to its NEW seat and holds:
        // translate(0,0) is the old seat shown now, translate(to-from) is the
        // new one; _finish's fs-snap then reaffirms the server frame where the
        // element already sits (no old-seat lurch). Self-inverse under from/to
        // swap → a reverse step glides it back. Same geometry as cursor_move.
        var el9=stage.querySelector(sel);
        if(el9){
          var pf=fromVal.split(',');
          var pt=toVal.split(',');
          var dx=parseFloat(pt[0])-parseFloat(pf[0]);
          var dy=parseFloat(pt[1])-parseFloat(pf[1]);
          var a9=el9.animate([
            {transform:'translate(0,0)'},
            {transform:'translate('+dx+'px,'+dy+'px)'}
          ],{duration:_dur(DUR),easing:'ease-out',fill:'forwards'});
          _anims.push(a9);pending.push(a9.finished);
        }
      }else if(kind==='annotation_remove'){
        var el7=_annEl(stage,target);
        if(el7){
          var a7=el7.animate([{opacity:1},{opacity:0}],
            {duration:_dur(DUR),easing:'ease-out',fill:'forwards'});
          _anims.push(a7);pending.push(a7.finished);
        }
      }else if(kind==='annotation_add'){
        var src8=_annEl(parsed,target);
        if(src8){
          var clone8=document.adoptNode(src8.cloneNode(true));
          var srcParent=src8.parentNode;
          var parentShape=null;
          var _midTransforms=[];
          while(srcParent&&srcParent.nodeType===1){
            var ds=srcParent.getAttribute&&srcParent.getAttribute('data-shape');
            if(ds){parentShape=stage.querySelector('[data-shape="'+_cssEscape(ds)+'"]');break;}
            var _tr=srcParent.getAttribute('transform');
            if(_tr)_midTransforms.push(_tr);
            srcParent=srcParent.parentNode;
          }
          var container=parentShape||stage.querySelector('svg');
          if(container){
            var _insertNode=clone8;
            for(var _ti=0;_ti<_midTransforms.length;_ti++){
              var _wg=document.createElementNS('http://www.w3.org/2000/svg','g');
              _wg.setAttribute('transform',_midTransforms[_ti]);
              _wg.appendChild(_insertNode);
              _insertNode=_wg;
            }
            var pathEl=clone8.querySelector('path');
            if(pathEl&&typeof pathEl.getTotalLength==='function'){
              clone8.style.opacity='1';
              container.appendChild(_insertNode);
              var len=pathEl.getTotalLength();
              pathEl.style.strokeDasharray=len;
              pathEl.style.strokeDashoffset=len+'px';
              var polyEl=clone8.querySelector('polygon');
              if(polyEl)polyEl.setAttribute('opacity','0');
              var textEl=clone8.querySelector('text');
              if(textEl)textEl.setAttribute('opacity','0');
              var drawDone=new Promise(function(resolve){
                var start=performance.now();
                var headShown=false;
                function tick(now){
                  var t=Math.min((now-start)/_dur(DUR_PATH_DRAW),1);
                  var eased=1-Math.pow(1-t,3);
                  pathEl.style.strokeDashoffset=(len*(1-eased))+'px';
                  if(!headShown&&t>=0.7){
                    headShown=true;
                    if(polyEl){
                      polyEl.animate([{opacity:0},{opacity:1}],
                        {duration:_dur(DUR_ARROWHEAD),easing:'ease-out',fill:'forwards'});
                    }
                    if(textEl){
                      textEl.animate([{opacity:0},{opacity:1}],
                        {duration:_dur(DUR_ARROWHEAD),easing:'ease-out',fill:'forwards'});
                    }
                  }
                  if(t<1){requestAnimationFrame(tick);}
                  else{
                    pathEl.style.strokeDashoffset='0';
                    if(polyEl)polyEl.setAttribute('opacity','1');
                    resolve();
                  }
                }
                requestAnimationFrame(tick);
              });
              pending.push(drawDone);
            }else{
              clone8.style.opacity='0';
              container.appendChild(_insertNode);
              var a8=clone8.animate([{opacity:0},{opacity:1}],
                {duration:_dur(DUR),easing:'ease-out',fill:'forwards'}); // fade-in decelerates → ease-out
              _anims.push(a8);pending.push(a8.finished);
            }
          }
        }
      }else if(kind==='annotation_recolor'){
        // Mirror the recolor branch on the annotation group. Colors are
        // sanitized (":" -> "-") exactly like Python's annotation_color_class,
        // so "state:current" maps to the scriba-annotation-state-current class.
        var elar=_annEl(stage,target);
        if(elar){
          var car=elar.className.baseVal||elar.className||'';
          car=car.replace('scriba-annotation-'+String(fromVal).replace(/:/g,'-'),'scriba-annotation-'+String(toVal).replace(/:/g,'-'));
          if(elar.className.baseVal!==undefined)elar.className.baseVal=car;
          else elar.className=car;
        }
      }else if(kind==='cursor_move'){
        // A caret slides to its NEW seat and holds: translate(0,0) is the old
        // seat shown now, translate(delta) is the new one; _finish's fs-snap
        // then lands on the server frame where the caret already sits there.
        // Self-inverse under from/to swap → reverse slides it back, no branch.
        var elc=stage.querySelector('[data-annotation="'+_cssEscape(target)+'"]');
        if(elc){
          var cf=fromVal.split(','),ct=toVal.split(',');
          var cdx=parseFloat(ct[0])-parseFloat(cf[0]);
          var cdy=parseFloat(ct[1])-parseFloat(cf[1]);
          var ac=elc.animate([
            {transform:'translate(0,0)'},
            {transform:'translate('+cdx+'px,'+cdy+'px)'}
          ],{duration:_dur(DUR),easing:'cubic-bezier(0.16,1,0.3,1)',fill:'forwards'});
          _anims.push(ac);pending.push(ac.finished);
        }
      }
    }
    var _INV_KIND={annotation_add:'annotation_remove',annotation_remove:'annotation_add',element_add:'element_remove',element_remove:'element_add',highlight_on:'highlight_off',highlight_off:'highlight_on'};
    function _invertRec(r){
      // r = [target, prop, from, to, kind] -> swap from/to, map the kind (or
      // keep it: recolor/value_change/position_move/annotation_recolor/
      // cursor_move are self-inverse under a from/to swap).
      return [r[0],r[1],r[3],r[2],_INV_KIND[r[4]]||r[4]];
    }
    function _invertManifest(tr){var o=[];for(var i=0;i<tr.length;i++)o.push(_invertRec(tr[i]));return o;}
    function _manifestTargets(tr){var set={},out=[];for(var t=0;t<tr.length;t++){if(!set[tr[t][0]]){set[tr[t][0]]=1;out.push(tr[t][0]);}}return out;}
    function _changedTargets(a,b){
      // Union of the targets over the manifests skipped by a jump (exclusive of
      // the start frame, inclusive of the destination) — the cheap set the
      // delta-pulse needs without composing the manifests themselves.
      var lo=Math.min(a,b)+1,hi=Math.max(a,b),set={},out=[];
      for(var k=lo;k<=hi;k++){var tr=frames[k]&&frames[k].tr;if(!tr)continue;
        for(var t=0;t<tr.length;t++){if(!set[tr[t][0]]){set[tr[t][0]]=1;out.push(tr[t][0]);}}}
      return out;
    }
    function _emphasize(targets){
      // Delta-emphasis: a transient pulse on the identities that just changed,
      // so a reverse/jump arrival reads "these are what moved". Compositor-only
      // via the CSS class .scriba-emphasis (keyframe owned by the stylesheet);
      // this runtime only toggles the class. Gated by reduced-motion and the
      // per-widget opt-out; capped so a big jump never flashes a dozen cells.
      if(!_canAnim)return;
      if(W.getAttribute('data-scriba-no-emphasis')!=null)return;
      if(!targets||!targets.length||targets.length>EMPH_CAP)return;
      var myGen=_gen,els=[];
      for(var i=0;i<targets.length;i++){
        var el=stage.querySelector('[data-target="'+_cssEscape(targets[i])+'"]')||stage.querySelector('[data-annotation="'+_cssEscape(targets[i])+'"]');
        if(el){el.classList.add('scriba-emphasis');els.push(el);}
      }
      if(!els.length)return;
      setTimeout(function(){
        if(myGen!==_gen)return; // a superseding nav orphaned this removal
        for(var j=0;j<els.length;j++)els[j].classList.remove('scriba-emphasis');
      },DUR_EMPH);
    }
    function animateTransition(toIdx,manifest,fsFlag){
      if(_animState==='animating'){_cancelAnims();snapToFrame(toIdx);return;}
      var tr=manifest; // caller supplies it — frames[i].tr forward, or the inverse for a Prev
      if(!tr||!tr.length||!_canAnim){snapToFrame(toIdx);return;}
      _animState='animating';
      var myGen=_gen;
      // Commit the target index BEFORE the transition runs: a click landing
      // mid-animation must step from the committed frame, not the stale one
      // (stale cur swallowed rapid Next clicks and blocked Prev entirely).
      cur=toIdx;
      _updateControls(toIdx);
      var parsed=new DOMParser().parseFromString(frames[toIdx].svg,'image/svg+xml');
      var pending=[];
      var phase1=[],phase2=[];
      for(var t=0;t<tr.length;t++){
        var k=tr[t][4];
        if(k==='annotation_add'||k==='highlight_on')phase1.push(tr[t]);
        else phase2.push(tr[t]);
      }
      for(var i=0;i<phase1.length;i++)_applyTransition(phase1[i],parsed,pending);
      var needsSync=!!fsFlag; // the SOURCE frame's fs on a reverse (frames[cur].fs), not frames[toIdx].fs
      function _finish(fullSync){
        if(_animState!=='animating'||myGen!==_gen)return; // superseded — a rapid re-animate resets _animState, so the generation check is load-bearing
        if(fullSync){
          stage.innerHTML=frames[toIdx].svg;
        }
        // A03: update narration AFTER the SVG animation settles so that the
        // aria-live announcement fires once the visual is stable, not at the
        // start of the WAAPI transition (~220 ms early).
        narr.innerHTML=frames[toIdx].narration;
        subC.innerHTML=frames[toIdx].substory||'';
        subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
        _anims=[];_animState='idle';
        _emphasize(_manifestTargets(tr)); // ② pulse what changed, once the stage is settled
      }
      function _runPhase2(){
        if(myGen!==_gen)return; // orphaned staggered callback after a supersede — never touch the snapped stage
        for(var j=0;j<phase2.length;j++){
          _applyTransition(phase2[j],parsed,pending);
        }
        if(pending.length>0){
          Promise.all(pending).then(function(){_finish(needsSync||true);}).catch(function(){_finish(true);});
        }else if(needsSync){
          setTimeout(function(){_finish(true);},_dur(DUR)+DUR_SYNC_FUDGE);
        }else{
          _finish(false);
        }
      }
      if(phase1.length>0&&phase2.length>0){
        setTimeout(_runPhase2,_dur(DUR_STAGGER));
      }else{
        _runPhase2();
      }
    }
    function show(i,animate){
      var d=i-cur;
      if(animate&&_canAnim&&frames[i]){
        // Forward step: the manifest at i took cur -> i. Reverse step: the
        // manifest at cur took cur-1 -> cur, so step back = apply its inverse.
        // Both feed the SOURCE-frame fs so the fs-snap lands on server truth.
        if(d===1&&frames[i].tr){animateTransition(i,frames[i].tr,frames[i].fs);return;}
        if(d===-1&&frames[cur].tr){animateTransition(i,_invertManifest(frames[cur].tr),frames[cur].fs);return;}
      }
      // No tween available (jump, no manifest, or reduced motion): snap, and on
      // a >1-step jump pulse the union of skipped targets so the leap is legible.
      var from=cur;
      snapToFrame(i);
      if(animate&&Math.abs(d)>1)_emphasize(_changedTargets(from,i));
    }
    prev.addEventListener('click',function(){if(cur>0)show(cur-1,true);});
    next.addEventListener('click',function(){if(cur<frames.length-1)show(cur+1,true);});
    W.addEventListener('keydown',function(e){
      if(e.target.closest('.scriba-substory-widget'))return;
      if(e.key==='ArrowRight'||e.key===' '){e.preventDefault();if(cur<frames.length-1)show(cur+1,true);}
      if(e.key==='ArrowLeft'){e.preventDefault();if(cur>0)show(cur-1,true);}
    });

    if(typeof MutationObserver!=='undefined'){
      new MutationObserver(function(){_cancelAnims();if(cur>=0)snapToFrame(cur);})
        .observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
    }
    show(0,false);
  // __SCRIBA_CORE_END__
  }

  function _initAll(){
    // Find all widgets that have an associated JSON data island
    var islands=document.querySelectorAll('script[type="application/json"][id^="scriba-frames-"]');
    for(var i=0;i<islands.length;i++){
      var island=islands[i];
      var widgetId=island.id.replace(/^scriba-frames-/,'');
      var W=document.getElementById(widgetId);
      if(!W||W.dataset.scribaReady)continue;
      W.dataset.scribaReady='1';
      try{
        var frames=JSON.parse(island.textContent);
        _scribaInit(W,frames);
      }catch(err){
        // If JSON parse fails, widget stays non-interactive but page doesn't break
      }
    }
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',_initAll);
  }else{
    _initAll();
  }
})();
