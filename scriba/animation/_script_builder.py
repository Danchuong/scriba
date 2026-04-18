"""JS script-building helpers extracted from emitter.py (Wave D2).

Provides two functions that assemble the ``<script>`` block injected into
each interactive widget:

- ``_build_inline_script`` — legacy inline runtime (``inline_runtime=True``).
- ``_build_external_script`` — JSON island + external ``<script src>`` tag
  (CSP-safe, ``inline_runtime=False``).
"""

from __future__ import annotations

import html as _html
import json as _json

__all__ = [
    "_build_external_script",
    "_build_inline_script",
]


# ---------------------------------------------------------------------------
# Minimal local helpers (duplicated from emitter to avoid circular import)
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    """Escape text for use in HTML attributes."""
    return _html.escape(text, quote=True)


def _escape_js(text: str) -> str:
    """Escape text for embedding in a JS template literal (backtick string)."""
    return (
        text
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
        .replace("</script>", r"<\/script>")
        .replace("</style>", r"<\/style>")
    )


# ---------------------------------------------------------------------------
# Script builders
# ---------------------------------------------------------------------------


def _build_inline_script(scene_id: str, js_frames_str: str) -> str:
    """Build the legacy inline ``<script>`` block for a widget."""
    sid = _escape_js(scene_id)
    return f"""\
<script>
(function(){{
  var _cssEscape=(typeof CSS!=='undefined'&&CSS.escape)?CSS.escape:function(s){{return String(s).replace(/[^a-zA-Z0-9_-]/g,function(c){{return '\\\\'+c.charCodeAt(0).toString(16)+' ';}});}};
  var W=document.getElementById('{sid}');
  var frames=[
    {js_frames_str}
  ];
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
  var _motionMQ=window.matchMedia('(prefers-reduced-motion:reduce)');
  var _canAnim=(typeof Element.prototype.animate==='function')&&!_motionMQ.matches;
  (function(){{var _mh=function(ev){{_canAnim=(typeof Element.prototype.animate==='function')&&!ev.matches;}};if(_motionMQ.addEventListener){{_motionMQ.addEventListener('change',_mh);}}else if(_motionMQ.addListener){{_motionMQ.addListener(function(mq){{_mh({{matches:mq.matches}});}});}}}})()
  var DUR=180;          // ms — primary WAAPI transition baseline
  // DUR_PATH_DRAW is intentionally shorter than DUR: drawn annotations feel snappier
  // than discrete element adds because the stroke-draw motion already implies "appearing".
  // Unifying to DUR would make path draws feel sluggish. Keep distinct.
  var DUR_PATH_DRAW=120; // ms — annotation path stroke-draw
  var DUR_VALUE=100;     // ms — value-change scale bounce (snappier than baseline)
  var DUR_ARROWHEAD=36;  // ms — arrowhead/label fade after path draw (~2 frames @ 60fps)
  var DUR_STAGGER=50;    // ms — phase-1 → phase-2 gap (annotation/highlight before moves)
  var DUR_SYNC_FUDGE=20; // ms — extra margin for needsSync timeout beyond _dur(DUR)
  var _speed=parseFloat(W.getAttribute('data-scriba-speed'))||1;
  function _dur(ms){{return Math.round(ms/_speed);}}
  function _cancelAnims(){{
    for(var k=0;k<_anims.length;k++)try{{_anims[k].finish();}}catch(e){{}}
    _anims=[];_animState='idle';
  }}
  function initSub(el){{
    var fd=JSON.parse(el.getAttribute('data-scriba-frames'));
    var sc=0,ss=el.querySelector('.scriba-stage'),sn=el.querySelector('.scriba-narration');
    var sp=el.querySelector('.scriba-btn-prev'),sx=el.querySelector('.scriba-btn-next');
    var sr=el.querySelector('.scriba-step-counter'),sd=el.querySelectorAll('.scriba-dot');
    function sh(i){{sc=i;ss.innerHTML=fd[i].svg;sn.innerHTML=fd[i].narration;
      sr.textContent='Sub-step '+(i+1)+' / '+fd.length;
      sp.disabled=i===0;sx.disabled=i===fd.length-1;
      sd.forEach(function(d,j){{d.className='scriba-dot'+(j===i?' active':j<i?' done':'');}});
    }}
    sp.addEventListener('click',function(){{if(sc>0)sh(sc-1);}});
    sx.addEventListener('click',function(){{if(sc<fd.length-1)sh(sc+1);}});
    sh(0);
  }}
  function _updateControls(i){{
    ctr.textContent='Step '+(i+1)+' / '+frames.length;
    prev.disabled=i===0;
    next.disabled=i===frames.length-1;
    dots.forEach(function(d,j){{d.className='scriba-dot'+(j===i?' active':j<i?' done':'');}});
  }}
  function snapToFrame(i){{
    _cancelAnims();
    cur=i;
    stage.innerHTML=frames[i].svg;
    narr.innerHTML=frames[i].narration;
    subC.innerHTML=frames[i].substory||'';
    subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
    _updateControls(i);
  }}
  function _arrowheadAt(path,size){{
    var len=path.getTotalLength();
    var tip=path.getPointAtLength(len);
    var back=path.getPointAtLength(Math.max(0,len-size*1.5));
    var dx=tip.x-back.x,dy=tip.y-back.y;
    var d=Math.sqrt(dx*dx+dy*dy)||1;
    var ux=dx/d,uy=dy/d,px=-uy,py=ux;
    var hw=size*0.5;
    return tip.x+','+tip.y+' '+(tip.x-ux*size+px*hw)+','+(tip.y-uy*size+py*hw)+' '+(tip.x-ux*size-px*hw)+','+(tip.y-uy*size-py*hw);
  }}
  function _applyTransition(rec,parsed,pending){{
    var target=rec[0],prop=rec[1],fromVal=rec[2],toVal=rec[3],kind=rec[4];
    var sel='[data-target="'+_cssEscape(target)+'"]';
    if(kind==='recolor'){{
      var el=stage.querySelector(sel);
      if(el){{
        var cls=el.className.baseVal||el.className||'';
        cls=cls.replace('scriba-state-'+fromVal,'scriba-state-'+toVal);
        if(el.className.baseVal!==undefined)el.className.baseVal=cls;
        else el.className=cls;
      }}
    }}else if(kind==='value_change'){{
      var el2=stage.querySelector(sel);
      if(el2){{var txt=el2.querySelector('text');if(txt){{
        txt.textContent=toVal;
        if(_canAnim){{txt.animate([{{transform:'scale(1)'}},{{transform:'scale(1.15)'}},{{transform:'scale(1)'}}],
          {{duration:_dur(DUR_VALUE),easing:'ease-out'}});}}
      }}}}
    }}else if(kind==='highlight_on'){{
      var el3=stage.querySelector(sel);
      if(el3){{
        var c3=el3.className.baseVal||el3.className||'';
        if(c3.indexOf('scriba-highlighted')===-1){{
          c3+=' scriba-highlighted';
          if(el3.className.baseVal!==undefined)el3.className.baseVal=c3;
          else el3.className=c3;
        }}
      }}
    }}else if(kind==='highlight_off'){{
      var el4=stage.querySelector(sel);
      if(el4){{
        var c4=el4.className.baseVal||el4.className||'';
        c4=c4.replace(/\\s*scriba-highlighted/g,'');
        if(el4.className.baseVal!==undefined)el4.className.baseVal=c4;
        else el4.className=c4;
      }}
    }}else if(kind==='element_remove'){{
      var el5=stage.querySelector(sel);
      if(el5){{
        var a5=el5.animate([{{opacity:1}},{{opacity:0}}],
          {{duration:_dur(DUR),easing:'ease-in',fill:'forwards'}}); // fade-out accelerates → ease-in
        _anims.push(a5);pending.push(a5.finished);
      }}
    }}else if(kind==='element_add'){{
      var src=parsed.querySelector(sel);
      if(src){{
        var clone=document.adoptNode(src.cloneNode(true));
        clone.style.opacity='0';
        var srcP=src.parentNode;
        var pShape=null;
        while(srcP&&srcP.nodeType===1){{
          var ds2=srcP.getAttribute&&srcP.getAttribute('data-shape');
          if(ds2){{pShape=stage.querySelector('[data-shape="'+_cssEscape(ds2)+'"]');break;}}
          srcP=srcP.parentNode;
        }}
        var ct=pShape||stage.querySelector('svg');
        if(ct){{ct.appendChild(clone);
          var a6=clone.animate([{{opacity:0}},{{opacity:1}}],
            {{duration:_dur(DUR),easing:'ease-out',fill:'forwards'}}); // fade-in decelerates → ease-out
          _anims.push(a6);pending.push(a6.finished);
        }}
      }}
    }}else if(kind==='position_move'){{
      var el9=stage.querySelector(sel);
      if(el9){{
        var pf=fromVal.split(',');
        var pt=toVal.split(',');
        var dx=parseFloat(pf[0])-parseFloat(pt[0]);
        var dy=parseFloat(pf[1])-parseFloat(pt[1]);
        var a9=el9.animate([
          {{transform:'translate('+dx+'px,'+dy+'px)'}},
          {{transform:'translate(0,0)'}}
        ],{{duration:_dur(DUR),easing:'ease-out',fill:'forwards'}});
        _anims.push(a9);pending.push(a9.finished);
      }}
    }}else if(kind==='annotation_remove'){{
      var el7=stage.querySelector('[data-annotation="'+_cssEscape(target)+'"]');
      if(el7){{
        var a7=el7.animate([{{opacity:1}},{{opacity:0}}],
          {{duration:_dur(DUR),easing:'ease-out',fill:'forwards'}});
        _anims.push(a7);pending.push(a7.finished);
      }}
    }}else if(kind==='annotation_add'){{
      var src8=parsed.querySelector('[data-annotation="'+_cssEscape(target)+'"]');
      if(src8){{
        var clone8=document.adoptNode(src8.cloneNode(true));
        var srcParent=src8.parentNode;
        var parentShape=null;
        var _midTransforms=[];
        while(srcParent&&srcParent.nodeType===1){{
          var ds=srcParent.getAttribute&&srcParent.getAttribute('data-shape');
          if(ds){{parentShape=stage.querySelector('[data-shape="'+_cssEscape(ds)+'"]');break;}}
          var _tr=srcParent.getAttribute('transform');
          if(_tr)_midTransforms.push(_tr);
          srcParent=srcParent.parentNode;
        }}
        var container=parentShape||stage.querySelector('svg');
        if(container){{
          var _insertNode=clone8;
          for(var _ti=0;_ti<_midTransforms.length;_ti++){{
            var _wg=document.createElementNS('http://www.w3.org/2000/svg','g');
            _wg.setAttribute('transform',_midTransforms[_ti]);
            _wg.appendChild(_insertNode);
            _insertNode=_wg;
          }}
          var pathEl=clone8.querySelector('path');
          if(pathEl&&typeof pathEl.getTotalLength==='function'){{
            clone8.style.opacity='1';
            container.appendChild(_insertNode);
            var len=pathEl.getTotalLength();
            pathEl.style.strokeDasharray=len;
            pathEl.style.strokeDashoffset=len+'px';
            var polyEl=clone8.querySelector('polygon');
            if(polyEl)polyEl.setAttribute('opacity','0');
            var textEl=clone8.querySelector('text');
            if(textEl)textEl.setAttribute('opacity','0');
            var drawDone=new Promise(function(resolve){{
              var start=performance.now();
              var headShown=false;
              function tick(now){{
                var t=Math.min((now-start)/_dur(DUR_PATH_DRAW),1);
                var eased=1-Math.pow(1-t,3);
                pathEl.style.strokeDashoffset=(len*(1-eased))+'px';
                if(!headShown&&t>=0.7){{
                  headShown=true;
                  if(polyEl){{
                    polyEl.animate([{{opacity:0}},{{opacity:1}}],
                      {{duration:_dur(DUR_ARROWHEAD),easing:'ease-out',fill:'forwards'}});
                  }}
                  if(textEl){{
                    textEl.animate([{{opacity:0}},{{opacity:1}}],
                      {{duration:_dur(DUR_ARROWHEAD),easing:'ease-out',fill:'forwards'}});
                  }}
                }}
                if(t<1){{requestAnimationFrame(tick);}}
                else{{
                  pathEl.style.strokeDashoffset='0';
                  if(polyEl)polyEl.setAttribute('opacity','1');
                  resolve();
                }}
              }}
              requestAnimationFrame(tick);
            }});
            pending.push(drawDone);
          }}else{{
            clone8.style.opacity='0';
            container.appendChild(_insertNode);
            var a8=clone8.animate([{{opacity:0}},{{opacity:1}}],
              {{duration:_dur(DUR),easing:'ease-out',fill:'forwards'}}); // fade-in decelerates → ease-out
            _anims.push(a8);pending.push(a8.finished);
          }}
        }}
      }}
    }}
  }}
  function animateTransition(toIdx){{
    if(_animState==='animating'){{_cancelAnims();snapToFrame(toIdx);return;}}
    var tr=frames[toIdx]&&frames[toIdx].tr;
    if(!tr||!tr.length||!_canAnim){{snapToFrame(toIdx);return;}}
    _animState='animating';
    narr.innerHTML=frames[toIdx].narration;
    _updateControls(toIdx);
    var parsed=new DOMParser().parseFromString(frames[toIdx].svg,'image/svg+xml');
    var pending=[];
    var phase1=[],phase2=[];
    for(var t=0;t<tr.length;t++){{
      var k=tr[t][4];
      if(k==='annotation_add'||k==='highlight_on')phase1.push(tr[t]);
      else phase2.push(tr[t]);
    }}
    for(var i=0;i<phase1.length;i++)_applyTransition(phase1[i],parsed,pending);
    var needsSync=!!(frames[toIdx]&&frames[toIdx].fs);
    function _finish(fullSync){{
      cur=toIdx;
      if(fullSync){{
        stage.innerHTML=frames[toIdx].svg;
      }}
      subC.innerHTML=frames[toIdx].substory||'';
      subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
      _anims=[];_animState='idle';
    }}
    function _runPhase2(){{
      for(var j=0;j<phase2.length;j++){{
        _applyTransition(phase2[j],parsed,pending);
      }}
      if(pending.length>0){{
        Promise.all(pending).then(function(){{_finish(needsSync||true);}}).catch(function(){{_finish(true);}});
      }}else if(needsSync){{
        setTimeout(function(){{_finish(true);}},_dur(DUR)+DUR_SYNC_FUDGE);
      }}else{{
        _finish(false);
      }}
    }}
    if(phase1.length>0&&phase2.length>0){{
      setTimeout(_runPhase2,_dur(DUR_STAGGER));
    }}else{{
      _runPhase2();
    }}
  }}
  function show(i,animate){{
    if(animate&&i===cur+1&&frames[i]&&frames[i].tr&&_canAnim){{
      animateTransition(i);
    }}else{{
      snapToFrame(i);
    }}
  }}
  prev.addEventListener('click',function(){{if(cur>0)show(cur-1,false);}});
  next.addEventListener('click',function(){{if(cur<frames.length-1)show(cur+1,true);}});
  W.addEventListener('keydown',function(e){{
    if(e.target.closest('.scriba-substory-widget'))return;
    if(e.key==='ArrowRight'||e.key===' '){{e.preventDefault();if(cur<frames.length-1)show(cur+1,true);}}
    if(e.key==='ArrowLeft'){{e.preventDefault();if(cur>0)show(cur-1,false);}}
  }});
  if(typeof MutationObserver!=='undefined'){{
    new MutationObserver(function(){{_cancelAnims();if(cur>=0)snapToFrame(cur);}})
      .observe(document.documentElement,{{attributes:true,attributeFilter:['data-theme']}});
  }}
  show(0,false);
}})();
</script>"""


def _build_external_script(
    scene_id: str,
    json_frames: list[dict],
    asset_base_url: str,
) -> str:
    """Build the JSON island + external ``<script src>`` tag for a widget.

    The JSON island uses ``<script type="application/json">`` which browsers
    never execute, so it is safe under any ``script-src`` CSP policy.
    The runtime ``scriba.<hash>.js`` is referenced via SRI-bearing ``<script
    src=...>`` which passes ``script-src 'self'`` without ``'unsafe-inline'``.
    """
    from scriba.animation.runtime_asset import (
        RUNTIME_JS_FILENAME,
        RUNTIME_JS_SHA384,
    )

    island_id = f"scriba-frames-{_escape(scene_id)}"
    json_payload = _json.dumps(json_frames, separators=(",", ":"))

    base = asset_base_url.rstrip("/")
    if base:
        src = f"{base}/{RUNTIME_JS_FILENAME}"
    else:
        src = RUNTIME_JS_FILENAME

    return (
        f'<script type="application/json" id="{island_id}">'
        f"{json_payload}"
        f"</script>\n"
        f'<script src="{src}" integrity="sha384-{RUNTIME_JS_SHA384}"'
        f' crossorigin="anonymous" defer></script>'
    )
