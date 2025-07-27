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

// Material colors for different metals
const METAL_COLORS = {
    gold: 0xFFD700,      // Classic gold
    roseGold: 0xE8A398,  // Rose gold
    silver: 0xC0C0C0,    // Silver
    copper: 0xFF9966     // Copper
};

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

// Modified createRing function that accepts arc parameters
function createRing(size, startAngle = 0, endAngle = Math.PI * 2) {
    const ringData = RING_SIZES[size];
    const innerRadius = ringData.innerDiameter / 2;
    const outerRadius = ringData.outerDiameter / 2;
    const height = calculateRingHeight(size);

    // Create ring shape with specified arc
    const shape = new THREE.Shape();
    
    // Outer arc
    shape.absarc(0, 0, outerRadius, startAngle, endAngle, false);
    
    // Line to inner radius at end angle
    const endX = Math.cos(endAngle) * innerRadius;
    const endY = Math.sin(endAngle) * innerRadius;
    shape.lineTo(endX, endY);
    
    // Inner arc (going backwards)
    shape.absarc(0, 0, innerRadius, endAngle, startAngle, true);
    
    // Close the shape
    shape.closePath();

    // Extrude settings
    const extrudeSettings = {
        steps: 4,
        depth: height,
        bevelEnabled: true,
        bevelThickness: 0.1,
        bevelSize: 0.1,
        bevelSegments: 8,
        curveSegments: 64
    };

    const ringGeometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    ringGeometry.center();

    const selectedColor = document.querySelector('input[name="metalColor"]:checked').value;
    const material = new THREE.MeshPhongMaterial({
        color: METAL_COLORS[selectedColor],
        metalness: 0.8,
        roughness: 0.2
    });

    return new THREE.Mesh(ringGeometry, material);
}

// Modified createCurvedText to return text data including angular span
function createCurvedTextWithData(text, font, ringSize, letterSpacing) {
    const ringData = RING_SIZES[ringSize];
    const ringOuterRadius = ringData.outerDiameter / 2;
    const ringHeight = calculateRingHeight(ringSize);

    // Array to hold all letter geometries
    const letterGeometries = [];
    
    // Dynamic text parameters
    const textSize = calculateTextSize(ringSize);
    const textDepth = textSize * 0.5;

    // Fixed max arc of 180 degrees (π radians)
    const maxArcRadians = Math.PI;

    // Remove spaces for character count
    const textWithoutSpaces = text.replace(/ /g, '');
    const charCount = textWithoutSpaces.length;

    if (charCount === 0) {
        return {
            mesh: new THREE.Mesh(new THREE.BufferGeometry()),
            startAngle: 0,
            endAngle: 0,
            totalAngle: 0
        };
    }

    // Calculate angles
    const baseCharAngle = 0.12;
    const adjustedCharAngle = baseCharAngle * letterSpacing;
    const totalAngleNeeded = charCount * adjustedCharAngle;
    const totalAngle = Math.min(totalAngleNeeded, maxArcRadians);
    const actualCharAngle = charCount > 1 ? totalAngle / (charCount - 1) : 0;

    // Start from left side and go right
    const startAngle = totalAngle / 2 + Math.PI / 2;

    // Track the actual angular extent of the text
    let minAngle = startAngle;
    let maxAngle = startAngle - totalAngle;

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
        
        // Get the letter dimensions before transformation
        const letterHeight = bbox.max.y - bbox.min.y;
        const letterWidth = bbox.max.x - bbox.min.x;

        // Center the letter geometry in X and Y, but not Z
        textGeometry.translate(-centerX, -centerY, 0);

        // Calculate angle for this character (decreasing to go left-to-right)
        const angle = startAngle - charIndex * actualCharAngle;

        // Create transformation matrix
        const matrix = new THREE.Matrix4();
        
        // Position at ring's outer radius
        const radius = ringOuterRadius;
        
        // Position in X-Y plane (ring is along Z axis)
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        const z = 0;
        
        // Apply rotations in correct order
        const flipX = new THREE.Matrix4().makeRotationX(Math.PI);
        matrix.multiply(flipX);
        
        const flipY = new THREE.Matrix4().makeRotationY(Math.PI);
        matrix.multiply(flipY);
        
        const rotationZ = angle + Math.PI / 2;
        const rotZ = new THREE.Matrix4().makeRotationZ(rotationZ);
        matrix.multiply(rotZ);
        
        matrix.setPosition(x, y, z);
        
        // Apply matrix to geometry
        textGeometry.applyMatrix4(matrix);
        
        // Move outward
        const normalX = Math.cos(angle);
        const normalY = Math.sin(angle);
        
        const outwardOffset = (letterHeight / 2) + 0.1;
        textGeometry.translate(normalX * outwardOffset, normalY * outwardOffset, 0);
        
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

    const selectedColor = document.querySelector('input[name="metalColor"]:checked').value;
    const material = new THREE.MeshPhongMaterial({
        color: METAL_COLORS[selectedColor],
        metalness: 0.8,
        roughness: 0.2
    });

    // Add some padding to the angular extent
    const angularPadding = 0.1; // radians
    
    return {
        mesh: new THREE.Mesh(mergedGeometry, material),
        startAngle: minAngle + angularPadding,
        endAngle: maxAngle - angularPadding,
        totalAngle: totalAngle + 2 * angularPadding
    };
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
    
    const selectedColor = document.querySelector('input[name="metalColor"]:checked').value;
    const material = new THREE.MeshPhongMaterial({
        color: METAL_COLORS[selectedColor],
        metalness: 0.8,
        roughness: 0.2
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

// Modified updateRing function
function updateRing() {
    const text = document.getElementById('textInput').value || 'LOVE';
    const fontName = document.getElementById('fontSelect').value;
    const ringSize = document.getElementById('ringSize').value;
    const letterSpacing = parseFloat(document.getElementById('letterSpacing').value);

    if (!fonts[fontName]) {
        showStatus('Loading fonts...', 'normal');
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
        const textData = createCurvedTextWithData(text.toUpperCase(), fonts[fontName], ringSize, letterSpacing);
        textMesh = textData.mesh;

        // STEP 2: Calculate the arc for the ring (excluding text area)
        // The text occupies from endAngle to startAngle (since it goes right to left)
        // So the ring should go from startAngle to endAngle + 2π
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
        // For a group, we need to calculate volume differently
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
        
    } catch (error) {
        console.error('Error generating ring:', error);
        showStatus('Error generating ring. Please try different settings.', 'error');
    }
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
            meshToExport = new THREE.Mesh(mergedGeometry, new THREE.MeshPhongMaterial());
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
