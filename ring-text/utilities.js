// utilities.js

let fonts = {};

// Calculate volume of mesh
function calculateVolume(mesh) {
    const geometry = mesh.geometry;
    
    if (!geometry.isBufferGeometry) {
        console.error('Geometry must be BufferGeometry');
        return 0;
    }
    
    const positions = geometry.attributes.position;
    const indices = geometry.index;
    let volume = 0;
    
    if (indices) {
        // Indexed geometry
        for (let i = 0; i < indices.count; i += 3) {
            const a = indices.getX(i);
            const b = indices.getX(i + 1);
            const c = indices.getX(i + 2);
            
            const v1 = new THREE.Vector3().fromBufferAttribute(positions, a);
            const v2 = new THREE.Vector3().fromBufferAttribute(positions, b);
            const v3 = new THREE.Vector3().fromBufferAttribute(positions, c);
            
            // Calculate signed volume of tetrahedron
            volume += v1.dot(v2.cross(v3)) / 6;
        }
    } else {
        // Non-indexed geometry
        for (let i = 0; i < positions.count; i += 3) {
            const v1 = new THREE.Vector3().fromBufferAttribute(positions, i);
            const v2 = new THREE.Vector3().fromBufferAttribute(positions, i + 1);
            const v3 = new THREE.Vector3().fromBufferAttribute(positions, i + 2);
            
            volume += v1.dot(v2.cross(v3)) / 6;
        }
    }
    
    return Math.abs(volume);
}

// Calculate and display weight
function calculateAndDisplayWeight(mesh) {
    const volumeMM3 = calculateVolume(mesh);
    const volumeCM3 = volumeMM3 / 1000;
    const weightGrams = volumeCM3 * GOLD_DENSITY;

    const weightDisplay = document.getElementById('weight-display');
    weightDisplay.innerHTML = `
        Estimated Weight: ${weightGrams.toFixed(2)} grams
        <br>
        <small>Volume: ${volumeCM3.toFixed(3)} cm³</small>
    `;
    weightDisplay.style.display = 'block';
}

// Show status message
function showStatus(message, type = 'normal') {
    const statusElement = document.getElementById('status');
    statusElement.textContent = message;
    
    statusElement.classList.remove('error', 'success', 'warning');
    
    if (type === 'error') {
        statusElement.classList.add('error');
    } else if (type === 'success') {
        statusElement.classList.add('success');
    } else if (type === 'warning') {
        statusElement.classList.add('warning');
    }
}

// Load Three.js fonts
function loadFonts() {
    const fontLoader = new THREE.FontLoader();
    const fontNames = ['Monsieur La Doulaise_Regular', 'Imperial Script_Regular', 'Miss Fajardose_Regular',
    'Borel_Regular',
    'Leckerli One_Regular',
    'Meow Script_Regular',
    'Pacifico_Regular',
    'Yellowtail_Regular',
    'Kapakana_Regular',
    'Cookie_Regular',
    'Engagement_Regular',
    'Waterfall_Regular',
    'Ballet_Regular',
    'Birthstone_Regular',
    'Corinthia_Bold',
    'Corinthia_Regular',
];

    fontNames.forEach(fontName => {
        fontLoader.load(
            `./fonts/${fontName}.json`,
            (font) => {
                fonts[fontName] = font;
                if (Object.keys(fonts).length === fontNames.length) {
                    updateRing(); // Generate initial ring
                }
            },
            (xhr) => {
                console.log(`${fontName} ${(xhr.loaded / xhr.total * 100)}% loaded`);
            },
            (error) => {
                console.error(`Error loading ${fontName} font:`, error);
                showStatus(`Error loading ${fontName} font`, 'error');
            }
        );
    });
}

// Modified exportSTL to handle group
function exportSTL() {
    if (!finalMesh) {
        alert('Please generate a ring first');
        return;
    }

    showStatus('Exporting STL...', 'normal');

    try {
        const exporter = new THREE.STLExporter();
        
        // If finalMesh is a group, we need to merge its children
        let meshToExport;
        if (finalMesh.type === 'Group') {
            const geometries = [];
            finalMesh.children.forEach(child => {
                if (child.geometry) {
                    geometries.push(child.geometry.clone());
                }
            });
            
            const mergedGeometry = THREE.BufferGeometryUtils.mergeBufferGeometries(geometries);
            meshToExport = new THREE.Mesh(mergedGeometry, new THREE.MeshStandardMaterial());
        } else {
            meshToExport = finalMesh;
        }
        
        const stlString = exporter.parse(meshToExport);

        const blob = new Blob([stlString], { type: 'text/plain' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `ring_${document.getElementById('textInput').value}_size${document.getElementById('ringSize').value}.stl`;
        link.click();
        
        showStatus('STL exported successfully', 'success');
        
        // Clean up temporary mesh if we created one
        if (meshToExport !== finalMesh) {
            meshToExport.geometry.dispose();
            meshToExport.material.dispose();
        }
    } catch (error) {
        console.error('Error exporting STL:', error);
        showStatus('Error exporting STL', 'error');
    }
}
