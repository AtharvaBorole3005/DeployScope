async function refreshVersionMetadata() {
  try {
    const response = await fetch("/api/version", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return;

    const version = await response.json();
    document.querySelector("#app-version").textContent = version.version;
    document.querySelector("#build-number").textContent = version.build_number;
    document.querySelector("#commit-sha").textContent = version.commit_sha;
    document.querySelector("#deployment-status").textContent =
      version.deployment_status || "Unavailable";
    document.querySelector("#metadata-note").textContent =
      version.metadata?.is_local_development
        ? "Build metadata uses labelled local-development defaults until configured by a pipeline."
        : "Build metadata supplied by the configured environment; deployment status is not reported by the application.";
  } catch {
    // Server-rendered values remain available when the metadata request cannot complete.
  }
}

refreshVersionMetadata();
