// Skeleton.jsx
import React from "react";

export default function Skeleton({ className = "" }) {
  return <div className={`skeleton ${className}`} style={{backgroundSize:"400% 100%"}} />;
}
