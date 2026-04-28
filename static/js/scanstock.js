(function () {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("scanstock-theme");
  if (savedTheme) root.dataset.theme = savedTheme;

  const qs = (selector, scope = document) => scope.querySelector(selector);
  const qsa = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

  function getCookie(name) {
    return document.cookie
      .split(";")
      .map((cookie) => cookie.trim())
      .find((cookie) => cookie.startsWith(name + "="))
      ?.split("=")[1];
  }

  function setHidden(element, hidden) {
    if (element) element.classList.toggle("hidden", hidden);
  }

  function absoluteUrl(path) {
    if (!path) return "";
    try {
      return new URL(path, window.location.origin).toString();
    } catch (_) {
      return path;
    }
  }

  function normalizeRisk(value) {
    return String(value || "unknown").toLowerCase();
  }

  qsa("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
      localStorage.setItem("scanstock-theme", root.dataset.theme);
    });
  });

  const sidebar = qs("#sidebar");
  qs("[data-menu-toggle]")?.addEventListener("click", () => {
    sidebar?.classList.toggle("open");
  });

  qsa("[data-placeholder]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      showToast(button.dataset.placeholder || "This action is planned for a later release.");
    });
  });

  function showToast(message) {
    let stack = qs(".message-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "message-stack";
      document.body.appendChild(stack);
    }
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    stack.appendChild(toast);
    setTimeout(() => toast.remove(), 3600);
  }

  function setupScanner() {
    const form = qs("#scannerForm");
    if (!form) return;

    const dropzone = qs("#dropzone");
    const fileInput = qs("#documentInput");
    const loading = qs("#scanLoading");
    const errorBox = qs("#scanError");
    const result = qs("#scanResult");
    const originalPreview = qs("#originalPreview");
    const scannedPreview = qs("#scannedPreview");
    const ocrText = qs("#ocrText");
    const riskReasons = qs("#riskReasons");
    const downloadJpg = qs("#downloadJpg");
    const downloadPdf = qs("#downloadPdf");

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone?.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone?.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.remove("drag-over");
      });
    });

    dropzone?.addEventListener("drop", (event) => {
      const file = event.dataTransfer.files[0];
      if (file) {
        fileInput.files = event.dataTransfer.files;
        previewOriginal(file, originalPreview);
      }
    });

    fileInput?.addEventListener("change", () => {
      const file = fileInput.files[0];
      if (file) previewOriginal(file, originalPreview);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = fileInput.files[0];
      if (!file) {
        showScannerError("Choose a document image before running the scan.");
        return;
      }
      if (!file.type.startsWith("image/")) {
        showScannerError("Invalid file. Please upload a JPG, PNG, or camera image.");
        return;
      }

      const payload = new FormData();
      payload.append("image", file);
      payload.append("mode", qs("#scanMode")?.value || "bw");
      payload.append("lang", qs("#ocrLang")?.value || "eng+vie");

      setHidden(errorBox, true);
      setHidden(result, true);
      setHidden(loading, false);

      try {
        const response = await fetch("/api/scanner/scan/", {
          method: "POST",
          headers: { "X-CSRFToken": getCookie("csrftoken") || "" },
          body: payload,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(scannerErrorMessage(data));
        renderScannerResult(data);
      } catch (error) {
        showScannerError(error.message || "Server error while scanning the document.");
      } finally {
        setHidden(loading, true);
      }
    });

    qs("#copyOcr")?.addEventListener("click", () => {
      navigator.clipboard.writeText(ocrText.value || "");
      showToast("OCR text copied.");
    });

    function previewOriginal(file, image) {
      image.src = URL.createObjectURL(file);
    }

    function showScannerError(message) {
      errorBox.textContent = message;
      setHidden(errorBox, false);
      setHidden(loading, true);
    }

    function scannerErrorMessage(data) {
      const raw = data?.error_message || data?.detail || "Server error while scanning the document.";
      if (/tesseract/i.test(raw)) return "OCR failed. Tesseract may not be installed or configured correctly.";
      if (/document boundary|contour|paper/i.test(raw)) return "No document detected. Try a clearer image with visible paper edges.";
      if (/image|read/i.test(raw)) return "Invalid file. The upload could not be read as an image.";
      return raw;
    }

    function renderScannerResult(data) {
      const scannedUrl = absoluteUrl(data.scanned_image_url || data.scanned_image);
      const pdfUrl = absoluteUrl(data.pdf_file_url || data.pdf_file);
      const risk = normalizeRisk(data.fake_risk_level);
      const confidence = Number(data.document_confidence || 0);

      scannedPreview.src = scannedUrl;
      downloadJpg.href = scannedUrl;
      downloadPdf.href = pdfUrl;
      ocrText.value = data.ocr_text || "";
      qs("#documentType").textContent = data.document_type || "unknown";
      qs("#documentConfidence").textContent = `${Math.round(confidence * 100)}%`;
      qs("#riskLevel").textContent = risk;
      qs("#riskLevel").className = `risk-text risk-${risk}`;
      qs("#riskScore").textContent = data.fake_risk_score ?? 0;

      riskReasons.innerHTML = "";
      const reasons = Array.isArray(data.fake_reasons) ? data.fake_reasons : [];
      (reasons.length ? reasons : ["No suspicious indicators returned."]).forEach((reason) => {
        const item = document.createElement("li");
        item.textContent = reason;
        riskReasons.appendChild(item);
      });

      setHidden(result, false);
      result.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function setupPlagiarism() {
    const form = qs("#plagiarismForm");
    if (!form) return;

    const empty = qs("#plagiarismEmpty");
    const loading = qs("#plagiarismLoading");
    const result = qs("#plagiarismResult");
    const errorBox = qs("#plagiarismError");
    const textarea = qs("#plagiarismText");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = textarea.value.trim();
      if (text.split(/\s+/).filter(Boolean).length < 3) {
        showPlagiarismError("Text must contain at least 3 words.");
        return;
      }

      setHidden(empty, true);
      setHidden(result, true);
      setHidden(errorBox, true);
      setHidden(loading, false);

      try {
        const response = await fetch("/api/plagiarism/check/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken") || "",
          },
          body: JSON.stringify({ text }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data?.text?.[0] || data?.detail || "Server error while checking similarity.");
        renderPlagiarismResult(data, text);
      } catch (error) {
        showPlagiarismError(error.message || "Server error while checking similarity.");
      } finally {
        setHidden(loading, true);
      }
    });

    function showPlagiarismError(message) {
      errorBox.textContent = message;
      setHidden(errorBox, false);
      setHidden(loading, true);
      setHidden(empty, false);
    }

    function renderPlagiarismResult(data, inputText) {
      const score = Number(data.similarity_percent || 0);
      const risk = score > 60 ? "High" : score > 25 ? "Medium" : "Low";
      const excerpt = data.matched_excerpt || "No excerpt available.";
      const title = data.matched_document?.title || "No reference match";

      qs("#similarityCircle").style.setProperty("--score", String(Math.max(0, Math.min(100, score))));
      qs("#similarityPercent").textContent = `${score.toFixed(1)}%`;
      qs("#plagiarismRisk").textContent = risk;
      qs("#plagiarismRisk").className = `risk-text risk-${risk.toLowerCase()}`;
      qs("#matchedTitle").textContent = title;
      qs("#matchedExcerpt").innerHTML = highlightExcerpt(excerpt, inputText);

      setHidden(result, false);
    }

    function highlightExcerpt(excerpt, inputText) {
      const terms = inputText
        .toLowerCase()
        .split(/\W+/)
        .filter((term) => term.length > 4)
        .slice(0, 8);
      let safe = escapeHtml(excerpt);
      terms.forEach((term) => {
        const pattern = new RegExp(`\\b(${escapeRegExp(term)})\\b`, "gi");
        safe = safe.replace(pattern, '<span class="excerpt-highlight">$1</span>');
      });
      return safe;
    }
  }

  function setupHistoryModal() {
    const modal = qs("#scanDetailModal");
    if (!modal) return;

    qsa("[data-open-detail]").forEach((button) => {
      button.addEventListener("click", () => {
        const card = button.closest("[data-detail]");
        if (!card) return;
        qs("#detailOriginal").src = card.dataset.original || "";
        qs("#detailScanned").src = card.dataset.scanned || "";
        qs("#detailOcr").value = card.dataset.ocr || "";
        qs("#detailType").textContent = card.dataset.type || "unknown";
        qs("#detailConfidence").textContent = card.dataset.confidence || "0%";
        qs("#detailScore").textContent = card.dataset.score || "0";
        qs("#detailRisk").textContent = card.dataset.risk || "unknown";
        qs("#detailRisk").className = `risk-text risk-${normalizeRisk(card.dataset.risk)}`;
        qs("#detailPdf").href = card.dataset.pdf || "#";

        const list = qs("#detailReasons");
        list.innerHTML = "";
        const reasons = (card.dataset.reasons || "").split(" | ").filter(Boolean);
        (reasons.length ? reasons : ["No risk reasons available."]).forEach((reason) => {
          const item = document.createElement("li");
          item.textContent = reason;
          list.appendChild(item);
        });

        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
      });
    });

    qs("[data-close-modal]")?.addEventListener("click", closeScanModal);
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeScanModal();
    });
    qs("#detailCopy")?.addEventListener("click", () => {
      navigator.clipboard.writeText(qs("#detailOcr")?.value || "");
      showToast("OCR text copied.");
    });

    function closeScanModal() {
      modal.classList.add("hidden");
      modal.setAttribute("aria-hidden", "true");
    }
  }

  function setupReferenceModal() {
    const modal = qs("#referenceModal");
    if (!modal) return;

    qsa("[data-reference-view]").forEach((button) => {
      button.addEventListener("click", () => {
        qs("#referenceModalTitle").textContent = button.dataset.title || "Reference document";
        qs("#referenceModalContent").value = button.dataset.content || "";
        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
      });
    });

    qs("[data-close-reference]")?.addEventListener("click", closeReferenceModal);
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeReferenceModal();
    });

    function closeReferenceModal() {
      modal.classList.add("hidden");
      modal.setAttribute("aria-hidden", "true");
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  setupScanner();
  setupPlagiarism();
  setupHistoryModal();
  setupReferenceModal();
})();
