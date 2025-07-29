// main.js
// Debouncing variables
let updateTimeout;

// Debounced update function
function debouncedUpdateRing() {
    // Clear any existing timeout
    clearTimeout(updateTimeout);
    
    // Show that we're waiting
    showStatus('Updating...', 'normal');
    
    // Set a new timeout to update after the delay
    updateTimeout = setTimeout(() => {
        updateRing();
    }, DEBOUNCE_DELAY);
}

// Modified updateRing function to handle text that goes beyond 360 degrees
function updateRing() {
    const text = document.getElementById('textInput').value || 'LOVE';
    const fontName = document.getElementById('fontSelect').value;
    const ringSize = document.getElementById('ringSize').value;
    const letterSpacing = parseFloat(document.getElementById('letterSpacing').value);
    const textOrientation = document.querySelector('input[name="textOrientation"]:checked').value;

    if (!fonts[fontName]) {
        showStatus('Loading fonts...', 'normal');
        return;
    }

    // Check if sleeping orientation is selected
    if (textOrientation === 'sleeping') {
        showStatus('Generating sleeping text...', 'normal');
        
        // Clear previous meshes
        if (finalMesh) {
            scene.remove(finalMesh);
            if (finalMesh.geometry) {
                finalMesh.geometry.dispose();
            }
            if (finalMesh.material) {
                finalMesh.material.dispose();
            }
            // If it's a group, dispose children
            if (finalMesh.children) {
                finalMesh.children.forEach(child => {
                    if (child.geometry) child.geometry.dispose();
                    if (child.material) child.material.dispose();
                });
            }
        }
        
        try {
            // STEP 1: Create sleeping text first and get angular data
            const textData = createCurvedTextSleeping(text, fonts[fontName], ringSize, letterSpacing);
            textMesh = textData.mesh;
            
            // STEP 2: Calculate the arc for the ring (excluding text area)
            const gapStart = textData.startAngle;
            const gapEnd = textData.endAngle;
            
            // Check if text spans more than full circle
            if (textData.totalAngle >= Math.PI * 2) {
                // Text fills entire ring, no ring to show
                finalMesh = textMesh;
                scene.add(finalMesh);
                
                showStatus('Text fills entire ring', 'warning');
            } else {
                // Create ring from gapEnd to gapStart + 2π (going the long way around)
                ringMesh = createRing(ringSize, gapEnd, gapStart + Math.PI * 2);
                
                // Combine ring and text
                const group = new THREE.Group();
                group.add(ringMesh);
                group.add(textMesh);
                finalMesh = group;
                scene.add(finalMesh);
            }
            
            // Calculate and display weight
            let totalVolume = 0;
            if (ringMesh) {
                totalVolume += calculateVolume(ringMesh);
            }
            totalVolume += calculateVolume(textMesh);
            
            const volumeCM3 = totalVolume / 1000;
            const weightGrams = volumeCM3 * GOLD_DENSITY;

            const weightDisplay = document.getElementById('weight-display');
            weightDisplay.innerHTML = `
                Estimated Weight: ${weightGrams.toFixed(2)} grams
                <br>
                <small>Volume: ${volumeCM3.toFixed(3)} cm³</small>
                <br>
                <small>Text angular span: ${(textData.totalAngle * 180 / Math.PI).toFixed(1)}°</small>
            `;
            weightDisplay.style.display = 'block';
            
            showStatus('Ready', 'success');
            
        } catch (error) {
            console.error('Error generating sleeping text:', error);
            showStatus('Error generating sleeping text. Please try different settings.', 'error');
        }
        
        return;
    }

    showStatus('Generating...', 'normal');

    // Clear previous meshes
    if (finalMesh) {
        scene.remove(finalMesh);
        if (finalMesh.geometry) {
            finalMesh.geometry.dispose();
        }
        if (finalMesh.material) {
            finalMesh.material.dispose();
        }
        // If it's a group, dispose children
        if (finalMesh.children) {
            finalMesh.children.forEach(child => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) child.material.dispose();
            });
        }
    }

    try {
        // STEP 1: Create curved text first and get angular data
        const textData = createCurvedTextWithData(text, fonts[fontName], ringSize, letterSpacing);
        textMesh = textData.mesh;

        // Check if text spans more than full circle
        if (textData.totalAngle >= Math.PI * 2) {
            // Text fills entire ring, no ring to show
            finalMesh = textMesh;
            scene.add(finalMesh);
            
            showStatus('Text fills entire ring', 'warning');
            
            const textVolume = calculateVolume(textMesh);
            const volumeCM3 = textVolume / 1000;
            const weightGrams = volumeCM3 * GOLD_DENSITY;

            const weightDisplay = document.getElementById('weight-display');
            weightDisplay.innerHTML = `
                Estimated Weight: ${weightGrams.toFixed(2)} grams
                <br>
                <small>Volume: ${volumeCM3.toFixed(3)} cm³</small>
                <br>
                <small>Text angular span: ${(textData.totalAngle * 180 / Math.PI).toFixed(1)}°</small>
            `;
            weightDisplay.style.display = 'block';
        } else {
            // STEP 2: Calculate the arc for the ring (excluding text area)
            const ringStartAngle = textData.startAngle;
            const ringEndAngle = textData.endAngle + Math.PI * 2;

            // STEP 3: Create ring with gap for text
            ringMesh = createRing(ringSize, ringStartAngle, ringEndAngle);

            // Combine ring and text
            const group = new THREE.Group();
            group.add(ringMesh);
            group.add(textMesh);
            finalMesh = group;
            scene.add(finalMesh);

            // Calculate and display weight
            const ringVolume = calculateVolume(ringMesh);
            const textVolume = calculateVolume(textMesh);
            const totalVolume = ringVolume + textVolume;
            
            const volumeCM3 = totalVolume / 1000;
            const weightGrams = volumeCM3 * GOLD_DENSITY;

            const weightDisplay = document.getElementById('weight-display');
            weightDisplay.innerHTML = `
                Estimated Weight: ${weightGrams.toFixed(2)} grams
                <br>
                <small>Volume: ${volumeCM3.toFixed(3)} cm³</small>
                <br>
                <small>Text angular span: ${(textData.totalAngle * 180 / Math.PI).toFixed(1)}°</small>
            `;
            weightDisplay.style.display = 'block';

            showStatus('Ready', 'success');
        }
        
    } catch (error) {
        console.error('Error generating ring:', error);
        showStatus('Error generating ring. Please try different settings.', 'error');
    }
}

// Initialize on load
window.addEventListener('load', init);
