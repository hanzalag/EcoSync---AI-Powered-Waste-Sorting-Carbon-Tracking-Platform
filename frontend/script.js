const API_BASE = 'http://127.0.0.1:5000/api';

let selectedBase64Image = '';
let impactChart = null;

// DOM Elements
const fileInput = document.getElementById('file-input');
const dropzonePrompt = document.getElementById('dropzone-prompt');
const imagePreview = document.getElementById('image-preview');
const wasteText = document.getElementById('waste-text');
const btnAnalyzeWaste = document.getElementById('btn-analyze-waste');
const wasteLoader = document.getElementById('waste-loader');
const wasteResult = document.getElementById('waste-result');

const carbonText = document.getElementById('carbon-text');
const btnCalculateCarbon = document.getElementById('btn-calculate-carbon');
const carbonLoader = document.getElementById('carbon-loader');
const carbonResult = document.getElementById('carbon-result');

// File Upload Handler
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
            selectedBase64Image = event.target.result;
            imagePreview.src = selectedBase64Image;
            imagePreview.classList.remove('hidden');
            dropzonePrompt.classList.add('hidden');
        };
        reader.readAsDataURL(file);
    }
});

// Fetch Community Metrics and Update Dashboard
async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        const data = await res.json();
        
        document.getElementById('stat-items').textContent = data.total_items_sorted;
        document.getElementById('stat-co2').textContent = `${data.total_co2_saved_kg} kg`;
        document.getElementById('stat-points').textContent = `${data.total_eco_points} pts`;
        
        updateChart(data.category_breakdown);
    } catch (e) {
        console.error("Stats fetching error:", e);
    }
}

// Render Doughnut Chart
function updateChart(breakdown) {
    const ctx = document.getElementById('impactChart').getContext('2d');
    const labels = Object.keys(breakdown);
    const counts = Object.values(breakdown);

    if (impactChart) impactChart.destroy();

    const chartLabels = labels.length ? labels : ['No Items Sorted Yet'];
    const chartData = counts.length ? counts : [1];

    impactChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: chartLabels,
            datasets: [{
                data: chartData,
                backgroundColor: ['#10b981', '#38bdf8', '#f59e0b', '#ef4444', '#8b5cf6'],
                borderWidth: 2,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 11 } }
                }
            },
            cutout: '68%'
        }
    });
}

// Waste Inspection Call
btnAnalyzeWaste.addEventListener('click', async () => {
    const text = wasteText.value.trim();
    if (!text && !selectedBase64Image) {
        alert("Please upload a photo or enter a text description.");
        return;
    }

    wasteLoader.classList.remove('hidden');
    wasteResult.classList.add('hidden');

    try {
        const res = await fetch(`${API_BASE}/analyze-waste`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_b64: selectedBase64Image,
                item: text
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        // Populate Waste Output UI
        document.getElementById('waste-item-name').textContent = data.item_name || "Analyzed Item";
        document.getElementById('waste-badge').textContent = data.category || "General";
        document.getElementById('waste-decomposition').textContent = data.decomposition_years || "Unknown";
        document.getElementById('waste-points').textContent = `+${data.eco_points || 50} Pts`;
        document.getElementById('waste-upcycle').textContent = data.upcycle_idea || "No idea provided.";
        document.getElementById('waste-impact').textContent = data.environmental_impact || "Reduces resource demand.";

        // Render Material Tags
        const materialsContainer = document.getElementById('waste-materials');
        materialsContainer.innerHTML = '';
        (data.materials || ['General Waste']).forEach(mat => {
            const span = document.createElement('span');
            span.className = 'tag';
            span.textContent = mat;
            materialsContainer.appendChild(span);
        });

        // Render Step-by-Step Disposal Steps
        const stepsList = document.getElementById('waste-steps');
        stepsList.innerHTML = '';
        (data.steps || ['Dispose in designated bin.']).forEach(step => {
            const li = document.createElement('li');
            li.textContent = step;
            stepsList.appendChild(li);
        });

        wasteResult.classList.remove('hidden');
        fetchStats();
    } catch (err) {
        alert("Error analyzing item: " + err.message);
    } finally {
        wasteLoader.classList.add('hidden');
    }
});

// Carbon Calculation Call
btnCalculateCarbon.addEventListener('click', async () => {
    const activity = carbonText.value.trim();
    if (!activity) return alert("Enter an activity description first.");

    carbonLoader.classList.remove('hidden');
    carbonResult.classList.add('hidden');

    try {
        const res = await fetch(`${API_BASE}/carbon-footprint`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activity })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        // Populate Carbon Output UI
        document.getElementById('carbon-val').textContent = data.estimated_kg_co2 || "0.0";
        document.getElementById('eq-trees').textContent = `${data.equivalents?.trees_needed || 0}d`;
        document.getElementById('eq-car').textContent = `${data.equivalents?.car_miles || 0} mi`;
        document.getElementById('eq-phones').textContent = `${data.equivalents?.smartphones_charged || 0}`;

        document.getElementById('carbon-immediate').textContent = data.immediate_action || "Take immediate steps.";
        document.getElementById('carbon-habit').textContent = data.long_term_habit || "Adopt sustainable lifestyle habits.";

        carbonResult.classList.remove('hidden');
        fetchStats();
    } catch (err) {
        alert("Error calculating footprint: " + err.message);
    } finally {
        carbonLoader.classList.add('hidden');
    }
});

// Load Metrics on Initial Page Load
fetchStats();