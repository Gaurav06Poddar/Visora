import React, { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

const API = "/api/analyzers/";

function App() {
  const [analyzers, setAnalyzers] = useState([]);
  const [form, setForm] = useState({ name: "", stream_url: "", schema_fields: "" });
  const [editingAnalyzer, setEditingAnalyzer] = useState(null);
  const [reportFiles, setReportFiles] = useState({});
  const [summaryFiles, setSummaryFiles] = useState({});
  const [selectedReport, setSelectedReport] = useState({});
  const [selectedSummary, setSelectedSummary] = useState({});
  const [reportContents, setReportContents] = useState({});
  const [summaryContents, setSummaryContents] = useState({});

  useEffect(() => {
    fetchAnalyzers();
  }, []);


  useEffect(() => {
    const fetchSelectedReports = async () => {
      for (const analyzer of analyzers) {
        const selectedFile = selectedReport?.[analyzer.id];
        if (selectedFile) {
          try {
            const res = await axios.get(`/api/analyzers/${analyzer.id}/reports/${selectedFile}`);
            setReportContents(prev => ({
              ...prev,
              [analyzer.id]: res.data
            }));
          } catch (err) {
            console.error("Error fetching selected report content:", err);
          }
        }
      }
    };

    fetchSelectedReports();
  }, [selectedReport, analyzers]);


  useEffect(() => {
    const fetchSelectedSummaries = async () => {
      for (const analyzer of analyzers) {
        if (selectedSummary?.id === analyzer.id && selectedSummary?.file) {
          try {
            const res = await axios.get(`/api/analyzers/${analyzer.id}/summaries/${selectedSummary.file}`);
            setSummaryContents(prev => ({
              ...prev,
              [analyzer.id]: res.data
            }));
          } catch (err) {
            console.error("Error fetching selected summary content:", err);
          }
        }
      }
    };

    fetchSelectedSummaries();
  }, [selectedSummary, analyzers]);


  const fetchAnalyzers = async () => {
    try {
      const res = await axios.get(API);

      const analyzersWithFiles = await Promise.all(
        res.data.map(async (analyzer) => {
          const id = analyzer.id;

          let reportRes = [];
          let summaryRes = [];
          let defaultReportContent = null;

          try {
            const [r, s] = await Promise.all([
              axios.get(`/api/analyzers/${id}/report-files`),
              axios.get(`/api/analyzers/${id}/summary-files`)
            ]);
            reportRes = r.data;
            summaryRes = s.data;
          } catch (err) {
            console.warn(`Error loading files for analyzer ${id}`, err);
          }

          if (reportRes.length > 0) {
            const defaultReport = reportRes[0];
            try {
              const contentRes = await axios.get(`/api/analyzers/${id}/reports/${defaultReport}`);
              defaultReportContent = contentRes.data;
              setSelectedReport(prev => ({ ...prev, [id]: defaultReport }));
              setReportContents(prev => ({ ...prev, [id]: defaultReportContent }));
            } catch (e) {
              console.error(`Failed to fetch default report for analyzer ${id}`, e);
            }
          }

          if (summaryRes.length > 0) {
            setSelectedSummary(prev => ({ ...prev, [id]: summaryRes[0] }));
          }

          return {
            ...analyzer,
            reports: reportRes,
            summaries: summaryRes,
          };
        })
      );

      setAnalyzers(analyzersWithFiles);
    } catch (error) {
      console.error("Error fetching analyzers:", error);
    }
  };



  const handleCreate = async () => {
    try {
      const schema_fields = form.schema_fields.split(",").map(f => f.trim()).filter(f => f !== "");
      await axios.post(API, { ...form, schema_fields });
      setForm({ name: "", stream_url: "", schema_fields: "" });
      fetchAnalyzers();
    } catch (err) {
      console.error("Failed to create analyzer", err);
    }
  };

  const handleUpdate = async () => {
    const schema_fields = editingAnalyzer.schema_fields.split(",").map(f => f.trim()).filter(f => f !== "");
    await axios.put(`${API}${editingAnalyzer.id}`, { ...editingAnalyzer, schema_fields });
    setEditingAnalyzer(null);
    fetchAnalyzers();
  };

  const handleDelete = async (id) => {
    await axios.delete(`${API}${id}`);
    fetchAnalyzers();
  };

  const handleReportSelect = async (analyzerId, filename) => {
    setSelectedReport(prev => ({ ...prev, [analyzerId]: filename }));
    const res = await axios.get(`/api/analyzers/${analyzerId}/reports/${filename}`);
    setReportContents(prev => ({ ...prev, [analyzerId]: res.data }));
  };

  const handleSummarySelect = (analyzerId, filename) => {
    setSelectedSummary(prev => ({ ...prev, [analyzerId]: filename }));
  };
  return (
    <div className="container">
      <h1>CCTV Analyzer Dashboard</h1>

      <div className="form">
        <h2>{editingAnalyzer ? "Edit Analyzer" : "Create New Analyzer"}</h2>
        <input
          placeholder="Name"
          value={editingAnalyzer ? editingAnalyzer.name : form.name}
          onChange={(e) =>
            editingAnalyzer
              ? setEditingAnalyzer({ ...editingAnalyzer, name: e.target.value })
              : setForm({ ...form, name: e.target.value })
          }
        />
        <input
          placeholder="Stream URL"
          value={editingAnalyzer ? editingAnalyzer.stream_url : form.stream_url}
          onChange={(e) =>
            editingAnalyzer
              ? setEditingAnalyzer({ ...editingAnalyzer, stream_url: e.target.value })
              : setForm({ ...form, stream_url: e.target.value })
          }
        />
        <textarea
          placeholder="Schema Fields (comma-separated)"
          value={editingAnalyzer ? editingAnalyzer.schema_fields : form.schema_fields}
          onChange={(e) =>
            editingAnalyzer
              ? setEditingAnalyzer({ ...editingAnalyzer, schema_fields: e.target.value })
              : setForm({ ...form, schema_fields: e.target.value })
          }
        />
        <button onClick={editingAnalyzer ? handleUpdate : handleCreate}>
          {editingAnalyzer ? "Update" : "Create"}
        </button>
        {editingAnalyzer && <button onClick={() => setEditingAnalyzer(null)}>Cancel</button>}
      </div>
      
      <div className="list">
        <h2>Analyzers</h2>
        {analyzers.map((analyzer) => (

        <div key={analyzer.id} className="card">
          <h3>{analyzer.name}</h3>
          <p><strong>Stream URL:</strong> {analyzer.stream_url}</p>
          <p><strong>Schema:</strong> {analyzer.schema_fields.join(", ")}</p>

          <div className="card-actions">
            <button onClick={() =>
              setEditingAnalyzer({
                ...analyzer,
                schema_fields: analyzer.schema_fields.join(", ")
              })
            }>Edit</button>
            <button onClick={() => handleDelete(analyzer.id)}>Delete</button>
          </div>

          {/* Reports Dropdown */}
          <div style={{ marginTop: "1rem" }}>
            <label><strong>Reports:</strong></label>
            {analyzer.reports && analyzer.reports.length > 0 ? (
              <>
                <select
                  onChange={(e) => {
                    const selectedFile = e.target.value;
                    setSelectedReport(prev => ({ ...prev, [analyzer.id]: selectedFile }));
                  }}
                  value={selectedReport?.[analyzer.id] || ""}
                >
                  <option value="" disabled>Select a report</option>
                  {analyzer.reports.map((file, i) => (
                    <option key={i} value={file}>{file}</option>
                  ))}
                </select>

                {selectedReport?.[analyzer.id] && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <a
                      href={`/analyzers/${analyzer.id}/reports/${selectedReport[analyzer.id]}`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ marginRight: "0.5rem" }}
                    >
                      View
                    </a>
                    <a
                      href={`/analyzers/${analyzer.id}/reports/${selectedReport[analyzer.id]}`}
                      download
                    >
                      Download
                    </a>
                  </div>
                )}

                {reportContents?.[analyzer.id] && (
                  <pre
                    style={{
                      background: "#f5f5f5",
                      padding: "1rem",
                      marginTop: "1rem",
                      borderRadius: "6px",
                      maxHeight: "300px",
                      overflowY: "auto",
                    }}
                  >
                    {JSON.stringify(reportContents[analyzer.id], null, 2)}
                  </pre>
                )}
              </>
            ) : (
              <p>No reports available</p>
            )}
          </div>


          {/* Summaries Dropdown */}
          <div style={{ marginTop: "1rem" }}>
            <label><strong>Summaries:</strong></label>
            {analyzer.summaries && analyzer.summaries.length > 0 ? (
              <>
                <select
                  value={selectedSummary[analyzer.id] || ""}
                  onChange={async (e) => {
                    const filename = e.target.value;

                    // Only fetch if not already loaded
                    if (!summaryContents[analyzer.id] || selectedSummary[analyzer.id] !== filename) {
                      setSelectedSummary(prev => ({ ...prev, [analyzer.id]: filename }));

                      try {
                        const res = await axios.get(`/api/analyzers/${analyzer.id}/summaries/${filename}`);
                        setSummaryContents(prev => ({ ...prev, [analyzer.id]: res.data }));
                      } catch (err) {
                        console.error(`Error fetching summary for analyzer ${analyzer.id}:`, err);
                        setSummaryContents(prev => ({
                          ...prev,
                          [analyzer.id]: { error: "Failed to load summary." }
                        }));
                      }
                    }
                  }}
                >
                  <option value="" disabled>Select a summary</option>
                  {analyzer.summaries.map((file, i) => (
                    <option key={i} value={file}>{file}</option>
                  ))}
                </select>

                {selectedSummary[analyzer.id] && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <a
                      href={`/analyzers/${analyzer.id}/summaries/${selectedSummary[analyzer.id]}`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ marginRight: "0.5rem" }}
                    >
                      View
                    </a>
                    <a
                      href={`/analyzers/${analyzer.id}/summaries/${selectedSummary[analyzer.id]}`}
                      download
                    >
                      Download
                    </a>
                  </div>
                )}

                {summaryContents?.[analyzer.id] && (
                  <pre
                    style={{
                      background: "#f5f5f5",
                      padding: "1rem",
                      marginTop: "1rem",
                      borderRadius: "6px",
                      maxHeight: "300px",
                      overflowY: "auto",
                    }}
                  >
                    {typeof summaryContents[analyzer.id] === "object"
                      ? JSON.stringify(summaryContents[analyzer.id], null, 2)
                      : "Invalid summary format"}
                  </pre>
                )}
              </>
            ) : (
              <p>No summaries available</p>
            )}
          </div>


        </div>
        ))}
      </div>
    </div>
  );
}

export default App;
