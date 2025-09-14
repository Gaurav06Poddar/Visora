// App.jsx - polished UI, keeps your backend API shape
import React, { useEffect, useState, useRef, useCallback } from "react";
import axios from "axios";
import "./App.css";
import VideoPlayer from "./components/VideoPlayer";
import Skeleton from "./components/Skeleton";

/*
  Notes:
  - Keeps your existing backend routes (/api/analyzers, /report-files, /reports/:file, /summaries/:file)
  - Caches fetched report contents to avoid re-downloading on re-render
  - Debounces selection updates a little so UI stays smooth
  - Shows skeletons while loading
*/

const API = "/api/analyzers/";

function useDebouncedState(initial, delay = 200) {
  const [state, setState] = useState(initial);
  const timeoutRef = useRef(null);
  const setDebounced = (val) => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setState(val), delay);
  };
  return [state, setState, setDebounced];
}

function App() {
  const [analyzers, setAnalyzers] = useState([]);
  const [form, setForm] = useState({ name: "", stream_url: "", schema_fields: "" });
  const [editingAnalyzer, setEditingAnalyzer] = useState(null);
  const [reportFiles, setReportFiles] = useState({});
  const [summaryFiles, setSummaryFiles] = useState({});
  const [selectedReport, , setSelectedReportDebounced] = useDebouncedState({}, 200);
  const [selectedSummary, setSelectedSummary] = useState({});
  const [reportCache, setReportCache] = useState({});
  const [summaryCache, setSummaryCache] = useState({});
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);

  // fetch analyzers + files
  const fetchAnalyzers = useCallback(async () => {
    setFetching(true);
    try {
      const res = await axios.get(API);
      const list = Array.isArray(res.data) ? res.data : [];
      setAnalyzers(list);

      // fetch file lists in parallel but non-blocking for UI
      list.forEach(async (an) => {
        try {
          const [rres, sres] = await Promise.allSettled([
            axios.get(`/api/analyzers/${an.id}/report-files`),
            axios.get(`/api/analyzers/${an.id}/summary-files`)
          ]);
          if (rres.status === "fulfilled") setReportFiles(prev => ({ ...prev, [an.id]: rres.value.data || [] }));
          if (sres.status === "fulfilled") setSummaryFiles(prev => ({ ...prev, [an.id]: sres.value.data || [] }));
        } catch (e) {
          console.warn("file list fetch err", e);
        }
      });

    } catch (err) {
      console.error("Error fetching analyzers:", err);
    } finally {
      setFetching(false);
    }
  }, []);

  useEffect(() => { fetchAnalyzers(); }, [fetchAnalyzers]);

  // fetch selected report contents, with cache and abort
  useEffect(() => {
    const entries = Object.entries(selectedReport);
    if (!entries.length) return;
    const controllers = [];

    entries.forEach(([anId, file]) => {
      const id = anId;
      if (!file) return;
      // already cached?
      if (reportCache[id] && reportCache[id].filename === file) return;

      const ctrl = new AbortController();
      controllers.push(ctrl);
      axios.get(`/api/analyzers/${id}/reports/${file}`, { signal: ctrl.signal })
        .then(res => setReportCache(prev => ({ ...prev, [id]: { filename: file, data: res.data } })))
        .catch(err => {
          if (!axios.isCancel(err)) console.error("Report load failed", err);
        });
    });

    return () => controllers.forEach(c => c.abort && c.abort());
  }, [selectedReport, reportCache]);

  // fetch selected summary similar to reports (lightweight)
  useEffect(() => {
    Object.entries(selectedSummary).forEach(([id, file]) => {
      if (!file) return;
      if (summaryCache[id] && summaryCache[id].filename === file) return;
      axios.get(`/api/analyzers/${id}/summaries/${file}`)
        .then(res => setSummaryCache(prev => ({ ...prev, [id]: { filename: file, data: res.data } })))
        .catch(err => console.warn("Summary load failed", err));
    });
  }, [selectedSummary, summaryCache]);

  const handleCreate = async () => {
    setLoading(true);
    try {
      const schema_fields = form.schema_fields.split(",").map(s => s.trim()).filter(Boolean);
      await axios.post(API, { ...form, schema_fields });
      setForm({ name: "", stream_url: "", schema_fields: "" });
      await fetchAnalyzers();
    } catch (e) {
      console.error("Failed to create analyzer", e);
      alert("Failed to create analyzer. See console.");
    } finally { setLoading(false); }
  };

  const handleUpdate = async () => {
    setLoading(true);
    try {
      const schema_fields = editingAnalyzer.schema_fields.split(",").map(s => s.trim()).filter(Boolean);
      await axios.put(`${API}${editingAnalyzer.id}`, { ...editingAnalyzer, schema_fields });
      setEditingAnalyzer(null);
      await fetchAnalyzers();
    } catch (e) {
      console.error("update err", e);
    } finally { setLoading(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this analyzer?")) return;
    try {
      await axios.delete(`${API}${id}`);
      // optimistic UI
      setAnalyzers(prev => prev.filter(a => a.id !== id));
    } catch (e) {
      console.error(e);
      alert("Delete failed");
    }
  };

  const handleReportSelect = (analyzerId, filename) => {
    // local update for immediate UI, debounced cache fetch handles load
    setSelectedReportDebounced(prev => ({ ...prev, [analyzerId]: filename }));
  };

  const handleSummarySelect = (analyzerId, filename) => {
    setSelectedSummary(prev => ({ ...prev, [analyzerId]: filename }));
  };

  // small UI helpers
  const showReportPreview = (id) => {
    const entry = reportCache[id];
    if (!entry) return null;
    // If object, display prettified sample or abbreviated
    const data = entry.data;
    // If it's large, show keys/summary
    if (typeof data === "object") {
      // show top-level keys + shortened JSON
      const keys = Object.keys(data);
      const short = JSON.stringify(data, (k,v)=> (typeof v === "object" && v && Object.keys(v).length>8 ? "[...]" : v), 2);
      return { short, keys };
    } else {
      return { short: String(data).slice(0, 1000) };
    }
  };

  return (
    <div className="container">
      <div className="header">
        <div className="brand">
          <div className="logo">VA</div>
          <div>
            <div className="title">VideoAnalyzer — Dashboard</div>
            <div className="subtitle">Realtime previews · fast report browsing</div>
          </div>
        </div>
        <div className="row">
          <div className="small-muted">Status: {fetching ? "Refreshing…" : "Ready"}</div>
        </div>
      </div>

      <div className="card">
        <div style={{display:"flex", alignItems:"center", justifyContent:"space-between", gap:12}}>
          <div>
            <div style={{fontWeight:700}}>Create / Edit Analyzer</div>
            <div className="small-muted">Provide stream URL (HLS .m3u8 recommended) and schema fields</div>
          </div>
        </div>

        <div className="form-grid" style={{marginTop:12}}>
          <input className="input" placeholder="Name" value={editingAnalyzer ? editingAnalyzer.name : form.name}
            onChange={(e) => editingAnalyzer ? setEditingAnalyzer({...editingAnalyzer, name: e.target.value}) : setForm({...form, name: e.target.value})} />

          <input className="input" placeholder="Stream URL (http(s) or m3u8)" value={editingAnalyzer ? editingAnalyzer.stream_url : form.stream_url}
            onChange={(e) => editingAnalyzer ? setEditingAnalyzer({...editingAnalyzer, stream_url: e.target.value}) : setForm({...form, stream_url: e.target.value})} />

          <input className="input" placeholder="Schema fields (comma separated)" value={editingAnalyzer ? editingAnalyzer.schema_fields : form.schema_fields}
            onChange={(e) => editingAnalyzer ? setEditingAnalyzer({...editingAnalyzer, schema_fields: e.target.value}) : setForm({...form, schema_fields: e.target.value})} />

          <div style={{display:"flex", gap:8, justifyContent:"flex-end"}}>
            {editingAnalyzer ? (
              <>
                <button className="btn ghost" onClick={()=>setEditingAnalyzer(null)}>Cancel</button>
                <button className="btn" onClick={handleUpdate}>{loading ? "Saving..." : "Save"}</button>
              </>
            ) : (
              <button className="btn" onClick={handleCreate}>{loading ? "Creating..." : "Create"}</button>
            )}
          </div>
        </div>
      </div>

      <div className="grid">
        {analyzers.length === 0 && !fetching ? (
          <div className="card">
            <div style={{display:"flex", alignItems:"center", gap:12}}>
              <div style={{flex:1}}>
                <div style={{fontSize:18, fontWeight:700}}>No analyzers yet</div>
                <div className="small-muted">Create one above or check your backend.</div>
              </div>
              <div><button className="btn" onClick={fetchAnalyzers}>Refresh</button></div>
            </div>
          </div>
        ) : (
          analyzers.map((an) => {
            const preview = reportCache[an.id];
            const reportMeta = showReportPreview(an.id);

            return (
              <div key={an.id} className="card analyzer">
                <div className="preview">
                  <div className="live-badge"><span className="live-dot"></span>LIVE</div>
                  <VideoPlayer src={an.stream_url} />
                  <div className="overlay">
                    <button className="btn ghost" onClick={() => { navigator.clipboard.writeText(an.stream_url); }}>Copy</button>
                  </div>
                </div>

                <div className="info">
                  <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start"}}>
                    <div>
                      <h3>{an.name}</h3>
                      <div className="meta">Stream URL: <span className="small">{an.stream_url || "—"}</span></div>
                      <div className="meta">Schema: <span className="small">{(an.schema_fields || []).join(", ")}</span></div>
                    </div>

                    <div style={{display:"flex", flexDirection:"column", gap:8}}>
                      <button className="btn" onClick={() => setEditingAnalyzer({...an, schema_fields:(an.schema_fields||[]).join(", ")})}>Edit</button>
                      <button className="btn ghost" onClick={() => handleDelete(an.id)}>Delete</button>
                    </div>
                  </div>

                  <div className="select">
                    <div style={{flex:1}}>
                      <div style={{fontSize:13, color:"var(--muted)"}}>Reports</div>
                      {(!reportFiles[an.id]) ? (
                        <div style={{marginTop:8}}><Skeleton /></div>
                      ) : (reportFiles[an.id].length === 0 ? <div className="small-muted">No reports</div> :
                        <select value={selectedReport[an.id]||""} onChange={(e)=>handleReportSelect(an.id, e.target.value)}>
                          <option value="">-- select report --</option>
                          {reportFiles[an.id].map((f,i)=> <option key={i} value={f}>{f}</option>)}
                        </select>
                      )}
                    </div>

                    <div style={{width:160}}>
                      <div style={{fontSize:13, color:"var(--muted)"}}>Summaries</div>
                      {(!summaryFiles[an.id]) ? (
                        <div style={{marginTop:8}}><Skeleton /></div>
                      ) : (summaryFiles[an.id].length === 0 ? <div className="small-muted">No summaries</div> :
                        <select value={selectedSummary[an.id]||""} onChange={(e)=>{handleSummarySelect(an.id, e.target.value)}}>
                          <option value="">-- select --</option>
                          {summaryFiles[an.id].map((f,i)=> <option key={i} value={f}>{f}</option>)}
                        </select>
                      )}
                    </div>
                  </div>

                  {/* Report display */}
                  <div style={{marginTop:8}}>
                    {(!selectedReport[an.id]) ? (
                      <div className="small-muted">Select a report to preview its contents</div>
                    ) : (!reportCache[an.id]) ? (
                      <div style={{marginTop:8}}><Skeleton className="h-24" /></div>
                    ) : (
                      <div>
                        <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
                          <div className="small">Preview: <span className="success">{reportCache[an.id].filename}</span></div>
                          <div style={{display:"flex", gap:8}}>
                            <a href={`/analyzers/${an.id}/reports/${reportCache[an.id].filename}`} target="_blank" rel="noreferrer" className="btn ghost">Open</a>
                            <a href={`/analyzers/${an.id}/reports/${reportCache[an.id].filename}`} download className="btn">Download</a>
                          </div>
                        </div>

                        <div className="report" style={{marginTop:8}}>
                          {reportMeta ? (
                            <>
                              <div style={{fontSize:12, color:"var(--muted)"}}>Top-level keys: {reportMeta.keys ? reportMeta.keys.join(", ") : "—"}</div>
                              <pre style={{whiteSpace:"pre-wrap", wordBreak:"break-word", marginTop:8}}>{reportMeta.short}</pre>
                            </>
                          ) : <div className="small-muted">No preview</div>}
                        </div>
                      </div>
                    )}
                  </div>

                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default App;
