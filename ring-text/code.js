// ring-personalizer.js
let scene, camera, renderer, controls;
let ringMesh, textMesh, finalMesh;
let fonts = {};

// Ring dimensions based on size (in mm)
const RING_SIZES = {
    '16': { innerDiameter: 16.5, outerDiameter: 19.5 },
    '17': { innerDiameter: 17.3, outerDiameter: 20.3 },
    '18': { innerDiameter: 18.1, outerDiameter: 21.1 },
    '19': { innerDiameter: 19.0, outerDiameter: 22.0 },
    '19.5': { innerDiameter: 19.4, outerDiameter: 22.4 },
    '20': { innerDiameter: 19.8, outerDiameter: 22.8 },
    '21': { innerDiameter: 20.6, outerDiameter: 23.6 }
};

// Material properties
const GOLD_DENSITY = 19.3; // g/cm³

// Initialize Three.js scene
function init() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);

    // Camera setup
    camera = new THREE.PerspectiveCamera(
        75,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );
    camera.position.set(0, 0, 50);

    // Renderer setup
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    document.getElementById('canvas-container').appendChild(renderer.domElement);

    // Controls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 5);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    // Load fonts
    loadFonts();

    // Handle window resize
    window.addEventListener('resize', onWindowResize, false);

    animate();
}

// Load Three.js fonts
function loadFonts() {
    const fontLoader = new THREE.FontLoader();
    const fontNames = ['Monsieur La Doulaise_Regular', 'Imperial Script_Regular', 'Miss Fajardose_Regular'];

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

// Calculate dynamic ring height based on size
function calculateRingHeight(size) {
    const sizeNum = parseFloat(size);
    return 2.0 + (sizeNum - 16) * 0.08;
}

// Calculate dynamic text size based on ring size
function calculateTextSize(ringSize) {
    const sizeNum = parseFloat(ringSize);
    return 1.2 + (sizeNum - 16) * 0.06;
}

// Create ring geometry
function createRing(size) {
    const ringData = RING_SIZES[size];
    const innerRadius = ringData.innerDiameter / 2;
    const outerRadius = ringData.outerDiameter / 2;
    const height = calculateRingHeight(size);

    // Create ring using a shape with hole
    const shape = new THREE.Shape();
    
    // Outer circle
    shape.absarc(0, 0, outerRadius, 0, Math.PI * 2, false);
    
    // Inner circle (hole)
    const hole = new THREE.Path();
    hole.absarc(0, 0, innerRadius, 0, Math.PI * 2, true);
    shape.holes.push(hole);

    // Extrude settings
    const extrudeSettings = {
        steps: 2,
        depth: height,
        bevelEnabled: true,
        bevelThickness: 0.1,
        bevelSize: 0.1,
        bevelSegments: 2
    };

    const ringGeometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    ringGeometry.center();

    const material = new THREE.MeshPhongMaterial({
        color: 0xFFD700,
    });

    return new THREE.Mesh(ringGeometry, material);
}

// Create curved text using BufferGeometry
function createCurvedText(text, font, ringSize, letterSpacing, maxArcDegrees) {
    const ringData = RING_SIZES[ringSize];
    const ringOuterRadius = ringData.outerDiameter / 2;
    const ringHeight = calculateRingHeight(ringSize);

    // Array to hold all letter geometries
    const letterGeometries = [];
    
    // Dynamic text parameters
    const textSize = calculateTextSize(ringSize);
    const textDepth = textSize * 0.5;

    // Convert maxArc from degrees to radians
    const maxArcRadians = (maxArcDegrees * Math.PI) / 180;

    // Remove spaces for character count
    const textWithoutSpaces = text.replace(/ /g, '');
    const charCount = textWithoutSpaces.length;

    if (charCount === 0) {
        return new THREE.Mesh(new THREE.BufferGeometry());
    }

    // Calculate angles
    const baseCharAngle = 0.12;
    const adjustedCharAngle = baseCharAngle * letterSpacing;
    const totalAngleNeeded = charCount * adjustedCharAngle;
    const totalAngle = Math.min(totalAngleNeeded, maxArcRadians);
    const actualCharAngle = charCount > 1 ? totalAngle / (charCount - 1) : 0;

    // Add π/2 to start angle to move text from x-axis to y-axis
    const startAngle = -totalAngle / 2 + Math.PI / 2;

    let charIndex = 0;

    // Create each letter
    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        if (char === ' ') continue;

        const textGeometry = new THREE.TextGeometry(char, {
            font: font,
            size: textSize,
            height: textDepth,
            curveSegments: 12,
            bevelEnabled: true,
            bevelThickness: 0.03,
            bevelSize: 0.03,
            bevelSegments: 3
        });

        // Center the letter
        textGeometry.computeBoundingBox();
        const bbox = textGeometry.boundingBox;
        const centerX = (bbox.max.x - bbox.min.x) / 2;
        const centerY = (bbox.max.y - bbox.min.y) / 2;

        // Center the letter geometry
        textGeometry.translate(-centerX, -centerY, 0);

        // Calculate angle for this character
        const angle = startAngle + charIndex * actualCharAngle;

        // Create transformation matrix
        const matrix = new THREE.Matrix4();
        
        // First, position at origin with proper orientation
        // The text should face outward from the ring center
        
        // Position on the outer surface of the ring
        // Since the ring's axis is Z, we position in the X-Y plane
        const radius = ringOuterRadius + textDepth * 0.1; // Slightly outside the ring
        
        // Position in X-Y plane (ring is along Z axis)
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        const z = 0; // Center along the ring's height
        
        // Create rotation to face outward from center
        // Text should be perpendicular to the radius
        const rotationZ = angle + Math.PI / 2; // Rotate to be tangent to the circle
        
        // Apply rotation first, then translation
        matrix.makeRotationZ(rotationZ);
        matrix.setPosition(x, y, z);
        
        // Apply matrix to geometry
        textGeometry.applyMatrix4(matrix);
        
        letterGeometries.push(textGeometry);
        charIndex++;
    }

    // Merge all letter geometries
    let mergedGeometry;
    if (letterGeometries.length > 0) {
        mergedGeometry = THREE.BufferGeometryUtils.mergeBufferGeometries(letterGeometries);
    } else {
        mergedGeometry = new THREE.BufferGeometry();
    }

    const material = new THREE.MeshPhongMaterial({
        color: 0xFFD700,
    });

    return new THREE.Mesh(mergedGeometry, material);
}

// Combine ring and text into a single mesh
function combineRingAndText(ring, textMesh) {
    // Clone geometries to avoid modifying originals
    const ringGeometry = ring.geometry.clone();
    const textGeometry = textMesh.geometry.clone();
    
    // Merge geometries
    const geometries = [ringGeometry];
    
    // Only add text geometry if it has vertices
    if (textGeometry.attributes.position && textGeometry.attributes.position.count > 0) {
        geometries.push(textGeometry);
    }
    
    const mergedGeometry = THREE.BufferGeometryUtils.mergeBufferGeometries(geometries);
    
    const material = new THREE.MeshPhongMaterial({
        color: 0xFFD700,
    });
    
    return new THREE.Mesh(mergedGeometry, material);
}

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

// Update the ring
function updateRing() {
    const text = document.getElementById('textInput').value || 'LOVE';
    const fontName = document.getElementById('fontSelect').value;
    const ringSize = document.getElementById('ringSize').value;
    const letterSpacing = parseFloat(document.getElementById('letterSpacing').value);
    const maxArc = parseFloat(document.getElementById('maxArc').value);

    if (!fonts[fontName]) {
        showStatus('Loading fonts...', 'normal');
        return;
    }

    showStatus('Generating...', 'normal');

    // Clear previous meshes
    if (finalMesh) {
        scene.remove(finalMesh);
        finalMesh.geometry.dispose();
        finalMesh.material.dispose();
    }

    try {
        // Create ring
        ringMesh = createRing(ringSize);

        // Create curved text
        textMesh = createCurvedText(text.toUpperCase(), fonts[fontName], ringSize, letterSpacing, maxArc);

        // Combine ring and text into a single mesh
        finalMesh = combineRingAndText(ringMesh, textMesh);

        // Clean up temporary meshes
        ringMesh.geometry.dispose();
        textMesh.geometry.dispose();

        scene.add(finalMesh);

        // Calculate and display weight
        calculateAndDisplayWeight(finalMesh);

        showStatus('Ready', 'success');
        
    } catch (error) {
        console.error('Error generating ring:', error);
        showStatus('Error generating ring. Please try different settings.', 'error');
        
        // Fallback: just show ring and text separately
        if (ringMesh && textMesh) {
            const group = new THREE.Group();
            group.add(ringMesh);
            group.add(textMesh);
            finalMesh = group;
            scene.add(finalMesh);
            showStatus('Generated with simplified method', 'warning');
        }
    }
}

// Export to STL
function exportSTL() {
    if (!finalMesh) {
        alert('Please generate a ring first');
        return;
    }

    showStatus('Exporting STL...', 'normal');

    try {
        const exporter = new THREE.STLExporter();
        const stlString = exporter.parse(finalMesh);

        const blob = new Blob([stlString], { type: 'text/plain' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `ring_${document.getElementById('textInput').value}_size${document.getElementById('ringSize').value}.stl`;
        link.click();
        
        showStatus('STL exported successfully', 'success');
    } catch (error) {
        console.error('Error exporting STL:', error);
        showStatus('Error exporting STL', 'error');
    }
}

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// Handle window resize
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

// Initialize on load
window.addEventListener('load', init);
