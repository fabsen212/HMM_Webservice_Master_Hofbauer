document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    const stopBtn = document.getElementById("stop-analysis");

    if (form) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();

            const formData = new FormData(form);
            document.getElementById("analysis_status").innerHTML =
                "<div class='alert alert-warning'> Analysis in progress...</div>";

            document.getElementById("progress-container").style.display = "block";
            document.getElementById("progress-bar").value = 0;
            document.getElementById("progress-text").innerText = "0%";
            document.getElementById("stop-analysis").style.display = "inline-block";

            fetch("/upload", { method: "POST", body: formData })
                .then(async response => {
                    let data;
                    try {
                        data = await response.json();
                    } catch (e) {
                        const text = await response.text();
                        document.getElementById("analysis_status").innerHTML = `
                            <div class='alert alert-danger'> ${text || "Unknown server error."}</div>`;
                        return;
                    }

                    if (data.status === "processing") {
                        const jobIds = data.jobs;
                        window.currentJobs = jobIds;
                        checkJobsFinished(jobIds);
                    } else if (data.status === "error") {
                        document.getElementById("analysis_status").innerHTML = `
                            <div class='alert alert-danger'> ${data.error || "Unknown error occurred."}</div>`;
                        document.getElementById("stop-analysis").style.display = "none";
                    }
                })
                .catch(error => {
                    console.error(" Upload Error!:", error);
                    document.getElementById("analysis_status").innerHTML =
                        "<div class='alert alert-danger'> Error during upload!</div>";
                    document.getElementById("stop-analysis").style.display = "none";
                });
        });
    }

    function checkJobsFinished(jobIds) {
        if (jobIds.length === 0) {
            document.getElementById("analysis_status").innerHTML =
                "<div class='alert alert-danger'> No jobs received!</div>";
            document.getElementById("stop-analysis").style.display = "none";
            return;
        }

        const progressBar = document.getElementById("progress-bar");
        const progressText = document.getElementById("progress-text");
        const total = jobIds.length;

        let lastPercent = 0;
        let startTime = Date.now();
        let warningShown = false;

        const checkInterval = setInterval(() => {
            Promise.all(
                jobIds.map(id =>
                    fetch(`/status/${id}`).then(res => res.json())
                )
            ).then(statuses => {
                console.log("Job statuses:",statuses);
                const finished = statuses.filter(s => s.status && s.status.includes("finished")).length;
                const failed = statuses.some(s => !s || s.status === "failed");
                const percent = Math.floor((finished / total) * 100);
                if (percent > lastPercent) {
                    lastPercent = percent;
                    progressBar.value = percent;
                    progressText.innerText = `${percent}%`;
                }
                const elapsed = Date.now() - startTime;
                if (elapsed > 10 * 60 * 1000 && !warningShown) {
                    document.getElementById("analysis_status").innerHTML +=
                        "<div class='alert alert-warning mt-2'>Alignment is still running. Please be patient, this may take several more minutes.</div>";
                    warningShown = true;
                }
                if (failed) {
                    clearInterval(checkInterval);
                    document.getElementById("analysis_status").innerHTML +=
                        "<div class='alert alert-danger mt-2'>Analysis failed due to No-Matches!</div>";
                    document.getElementById("stop-analysis").style.display = "none";
                } 
                if (finished === total) {
                    clearInterval(checkInterval);
                    document.getElementById("analysis_status").innerHTML +=
                        "<div class='alert alert-success mt-2'>Analysis done! Redirecting to results...</div>";
                    document.getElementById("stop-analysis").style.display = "none";
                    setTimeout(() => {
                        window.location.href = "/results";
                    }, 5000);
                }
                const maxDuration = 60 * 60 * 1000;
                if (elapsed > maxDuration) {
                    clearInterval(checkInterval);
                    document.getElementById("analysis_status").innerHTML +=
                        "<div class='alert alert-warning'>Maximum runtime reached. Redirecting anyway...</div>";
                    window.location.href = "/results";
                }
            });
        }, 3000);
    }

    if (stopBtn) {
        stopBtn.addEventListener("click", () => {
            if (!window.currentJobs || window.currentJobs.length === 0) return;

            fetch("/cancel_jobs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_ids: window.currentJobs })
            })
                .then(res => res.json())
                .then(data => {
                    document.getElementById("analysis_status").innerHTML =
                        `<div class='alert alert-danger'> Analysis was stopped by user.</div>`;
                    document.getElementById("progress-text").innerText = "Stopped";
                    document.getElementById("stop-analysis").style.display = "none";
                })
                .catch(err => {
                    console.error("Failed to cancel jobs:", err);
                });
        });
    }

    window.fetchResults = function () {
        fetch('/get_results')
            .then(response => response.json())
            .then(data => {
                let resultDiv = document.getElementById("results");
                resultDiv.innerHTML = "";

                if (Object.keys(data).length === 0) {
                    resultDiv.innerHTML = "<p>No results available!</p>";
                    return;
                }

                for (let file in data) {
                    let resultSection = document.createElement("div");
                    let list = data[file].map(gene => `<li>${gene}</li>`).join('');
                    resultSection.innerHTML = `<h3>${file}</h3><ul>${list}</ul><hr>`;
                    resultDiv.appendChild(resultSection);
                }
            })
            .catch(error => console.error("Error loading the results:", error));
    };

    window.generateReport = function () {
        const format = document.getElementById("report_format").value;
        let url = "/generate_report_combined";
        let downloadUrl;

        if (format === "csv") {
            downloadUrl = "/download_csv";
        } else if (format === "pdf") {
            downloadUrl = "/download_report";
        } else if (format === "nwk") {
            window.location.href = "/download_tree";
            return;
        }

        const formData = new FormData();
        formData.append("format", format);

        fetch(url, { method: "POST", body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.job_id) {
                    const jobId = data.job_id;
                    const checkStatus = setInterval(() => {
                        fetch(`/status/${jobId}`)
                            .then(res => res.json())
                            .then(statusData => {
                                if (statusData.status === "finished") {
                                    clearInterval(checkStatus);
                                    window.location.href = downloadUrl;
                                } else if (statusData.status === "failed") {
                                    clearInterval(checkStatus);
                                    alert("❌ Error when creating the report.");
                                }
                            });
                    }, 1500);
                } else if (data.error) {
                    alert("Error: " + data.error);
                }
            })
            .catch(error => console.error("Error generating the report:", error));
    };

    const selectedSpecies = [];
    const speciesHidden = document.getElementById('species-hidden');
    const selector = document.getElementById('species-selector');
    const speciesSelect = document.getElementById('species-options');

    if (speciesSelect && selector && speciesHidden) {
        function updateUI() {
            selector.innerHTML = '';
            selectedSpecies.forEach((sp, index) => {
                const chip = document.createElement('span');
                chip.className = 'badge bg-primary text-white me-2 mb-2';
                chip.style.cursor = 'default';
                chip.innerHTML = `${index + 1}. ${sp} <span class="ms-1" style="cursor:pointer;" data-remove="${sp}">&times;</span>`;
                selector.appendChild(chip);
            });
            speciesHidden.value = selectedSpecies.join(',');
        }

        function removeSpecies(name) {
            const idx = selectedSpecies.indexOf(name);
            if (idx !== -1) {
                selectedSpecies.splice(idx, 1);
                updateUI();
            }
        }

        speciesSelect.addEventListener('change', (e) => {
            const selected = e.target.value;
            if (selected && !selectedSpecies.includes(selected)) {
                selectedSpecies.push(selected);
                updateUI();
            }
            e.target.selectedIndex = -1;
        });

        selector.addEventListener('click', (e) => {
            if (e.target && e.target.dataset.remove) {
                removeSpecies(e.target.dataset.remove);
            }
        });
    }
});

// Collapsible sections with navigation
document.querySelectorAll(".collapsible").forEach(button => {
    // For every element with class "collapsible", add a click listener
    button.addEventListener("click", function () {
        const targetId = this.dataset.target; // Read the value from data-target attribute of the button
        const targetSection = document.getElementById("section-" + targetId); // Find the section with ID "section-{targetId}"

        // Hide all currently visible collapsible contents
        document.querySelectorAll(".collapsible-content").forEach(content => {
            content.style.display = "none"; // Collapse every collapsible content
        });

        // Show only the target section's content
        if (targetSection) {
            const content = targetSection.querySelector(".collapsible-content"); // Find the collapsible content within the target section
            if (content) {
                content.style.display = "block"; // Expand the selected section
                // Scroll smoothly to the opened section (minus 60px for fixed nav offset)
                window.scrollTo({ top: targetSection.offsetTop - 60, behavior: "smooth" });
            }
        }
    });
});

// Zoomable image viewer (pan & zoom support)
const zoomImg = document.getElementById("zoom-image");         // The image element to zoom and pan
const zoomContainer = document.getElementById("zoom-container"); // The container that holds the image
const resetBtn = document.getElementById("reset-zoom");        // Button to reset zoom and position

// Only run this block if both image and container elements exist
if (zoomImg && zoomContainer) {
    let scale = 1;// Initial zoom level (1 = 100%)
    zoomImg.onload = function () {
        const widthRatio = zoomContainer.clientWidth / zoomImg.naturalWidth;
        const heightRatio = zoomContainer.clientHeight / zoomImg.naturalHeight;
        scale = Math.min(widthRatio, heightRatio); 
        translateX = 0;
        translateY = 0;
        updateTransform();
    };

    // Function to apply transformation (zoom + pan) to the image
    function updateTransform() {
        zoomImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    }

    // Zoom using the mouse wheel
    zoomContainer.addEventListener("wheel", (e) => {
        e.preventDefault(); // Prevent page scroll
        const delta = e.deltaY > 0 ? -0.1 : 0.1; // Zoom in (scroll up) or out (scroll down)
        scale = Math.min(Math.max(0.05, scale + delta), 5); // Clamp scale between 0.2 and 5
        updateTransform(); // Apply updated zoom
    });

    // Drag to pan the image with the mouse
    let isDragging = false; // Whether the user is currently dragging
    let startX, startY;     // Start position of the drag

    zoomContainer.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return; // Only respond to left mouse button
        isDragging = true;         // Enable dragging
        startX = e.clientX;        // Record initial X position
        startY = e.clientY;        // Record initial Y position
        zoomContainer.style.cursor = "grabbing"; // Change cursor style
    });

    window.addEventListener("mouseup", () => {
        isDragging = false;                     // Stop dragging on mouse up
        zoomContainer.style.cursor = "default"; // Reset cursor style
    });

    window.addEventListener("mousemove", (e) => {
        if (!isDragging) return; // Only move if dragging
        const dx = e.clientX - startX; // Change in X position
        const dy = e.clientY - startY; // Change in Y position
        startX = e.clientX; // Update starting point for next move
        startY = e.clientY;
        translateX += dx; // Move image horizontally
        translateY += dy; // Move image vertically
        updateTransform(); // Apply the updated position
    });

    // Reset zoom and pan when reset button is clicked
    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            scale = 1;
            translateX = 0;
            translateY = 0;
            updateTransform(); // Apply the reset state
        });
    }
}

