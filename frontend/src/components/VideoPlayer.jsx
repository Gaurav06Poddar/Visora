// VideoPlayer.jsx (updated) - lightweight player with fullscreen button
import React, { useEffect, useRef, useState } from "react";

export default function VideoPlayer({ src }) {
  const videoRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    // reset
    video.pause();
    video.removeAttribute('src');
    video.load();

    if (!src) return;

    const isM3U8 = typeof src === "string" && src.includes(".m3u8");
    let hlsInstance = null;
    let script = null;

    const playNative = () => {
      video.src = src;
      const p = video.play();
      if (p && p.catch) p.catch(()=>{ /* autoplay blocked */ });
    };

    if (isM3U8) {
      // try to use any globally available Hls or dynamically load hls.js from CDN
      const tryHls = async () => {
        try {
          if (window.Hls) {
            const Hls = window.Hls;
            hlsInstance = new Hls({ maxBufferLength: 6, maxMaxBufferLength: 12 });
            hlsInstance.loadSource(src);
            hlsInstance.attachMedia(video);
          } else {
            script = document.createElement("script");
            script.src = "https://unpkg.com/hls.js@1.4.0/dist/hls.min.js";
            script.async = true;
            script.onload = () => {
              if (window.Hls) {
                const Hls = window.Hls;
                hlsInstance = new Hls({ maxBufferLength: 6, maxMaxBufferLength: 12 });
                hlsInstance.loadSource(src);
                hlsInstance.attachMedia(video);
                const p = video.play();
                if (p && p.catch) p.catch(()=>{});
              } else {
                playNative();
              }
            };
            script.onerror = () => playNative();
            document.body.appendChild(script);
          }
        } catch (e) {
          console.warn("HLS load failed, fallback native", e);
          playNative();
        }
      };
      tryHls();
    } else {
      playNative();
    }

    return () => {
      if (hlsInstance && hlsInstance.destroy) try { hlsInstance.destroy(); } catch(e){}
      if (script && script.parentNode) script.parentNode.removeChild(script);
    };
  }, [src]);

  const handleFullscreen = () => {
    const el = videoRef.current;
    if (!el) return;
    // try container fullscreen for a nicer look
    const container = el.parentElement;
    if (!document.fullscreenElement) {
      container.requestFullscreen?.().catch(()=>{});
    } else {
      document.exitFullscreen?.().catch(()=>{});
    }
  };

  return (
    <div style={{position:"relative"}}>
      <video ref={videoRef} playsInline muted controls={false} style={{width:"100%", height:320, display:"block", background:"#000"}} />
      <div style={{position:"absolute", right:8, bottom:8}}>
        <button className="btn" onClick={handleFullscreen} style={{padding:"8px 10px", fontSize:13}}>Fullscreen</button>
      </div>
      {error && <div style={{color:"salmon", fontSize:12}}>{error}</div>}
    </div>
  );
}
