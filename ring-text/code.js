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
            `./6_fonts/${fontName}.json`,  // Changed to local path
            (font) => {
                fonts[fontName] = font;
                if (Object.keys(fonts).length === fontNames.length) {
                    updateRing(); // Generate initial ring
                }
            },
            // Progress callback (optional)
            (xhr) => {
                console.log(`${fontName} ${(xhr.loaded / xhr.total * 100)}% loaded`);
            },
            // Error callback
            (error) => {
                console.error(`Error loading ${fontName} font:`, error);
                document.getElementById('status').textContent = `Error loading ${fontName} font`;
            }
        );
    });
}

// Create ring geometry
function createRing(size) {
    const ringData = RING_SIZES[size];
    const innerRadius = ringData.innerDiameter / 2;
    const outerRadius = ringData.outerDiameter / 2;
    const height = 2.5; // Ring height in mm

    // Create ring using RingGeometry extruded
    const shape = new THREE.Shape();
    
    // Outer circle
    shape.absarc(0, 0, outerRadius, 0, Math.PI * 2, false);
    
    // Inner circle (hole)
    const hole = new THREE.Path();
    hole.absarc(0, 0, innerRadius, 0, Math.PI * 2, true);
    shape.holes.push(hole);
    
    // Extrude settings
    const extrudeSettings = {
        steps: 1,
        depth: height,
        bevelEnabled: false
    };
    
    const ringGeometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    
    // Center the geometry
    ringGeometry.center();
    
    const material = new THREE.MeshPhongMaterial({
        color: 0xFFD700,
        metalness: 0.8,
        roughness: 0.2
    });

    return new THREE.Mesh(ringGeometry, material);
}

// Create curved text - with user-controlled spacing and arc
function createCurvedText(text, font, ringSize, letterSpacing, maxArcDegrees) {
    const ringData = RING_SIZES[ringSize];
    const ringOuterRadius = ringData.outerDiameter / 2;
    const ringHeight = 2.5; // Ring height in mm
    
    // Create a group to hold all letters
    const textGroup = new THREE.Group();

    // Text parameters
    const textSize = 1.5; // Slightly smaller for better fit
    const textDepth = 0.6; // Depth of text extrusion

    // Convert maxArc from degrees to radians
    const maxArcRadians = (maxArcDegrees * Math.PI) / 180;
    
    // Remove spaces for character count
    const textWithoutSpaces = text.replace(/ /g, '');
    const charCount = textWithoutSpaces.length;
    
    if (charCount === 0) return textGroup;

    // Calculate angle per character with letter spacing
    const baseCharAngle = 0.12; // Base angle per character
    const adjustedCharAngle = baseCharAngle * letterSpacing;
    
    // Calculate total angle needed for text
    const totalAngleNeeded = charCount * adjustedCharAngle;
    
    // Use either the needed angle or max arc, whichever is smaller
    const totalAngle = Math.min(totalAngleNeeded, maxArcRadians);
    
    // Calculate actual angle per character (might be compressed if hitting max arc)
    const actualCharAngle = charCount > 1 ? totalAngle / (charCount - 1) : 0;
    const startAngle = -totalAngle / 2;

    // Track character index (excluding spaces)
    let charIndex = 0;

    // Create each letter
    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        
        if (char === ' ') continue; // Skip spaces

        const textGeometry = new THREE.TextGeometry(char, {
            font: font,
            size: textSize,
            height: textDepth,
            curveSegments: 12,
            bevelEnabled: true,
            bevelThickness: 0.05,
            bevelSize: 0.05,
            bevelSegments: 5
        });

        // Center the letter geometry
        textGeometry.computeBoundingBox();
        const bbox = textGeometry.boundingBox;
        const centerX = (bbox.max.x - bbox.min.x) / 2;
        const centerY = (bbox.max.y - bbox.min.y) / 2;
        
        // Important: Center in Z direction too
        textGeometry.translate(-centerX, -centerY, 0);

        const letterMesh = new THREE.Mesh(
            textGeometry,
            new THREE.MeshPhongMaterial({ 
                color: 0xFFD700,
                metalness: 0.8,
                roughness: 0.2
            })
        );

        // Calculate angle for this character
        const angle = startAngle + charIndex * actualCharAngle;

        // Position letter on the ring's outer surface
        const radius = ringOuterRadius + 0.1;
        
        letterMesh.position.x = Math.sin(angle) * radius;
        letterMesh.position.z = Math.cos(angle) * radius;
        letterMesh.position.y = 0; 

        // Rotate letter to be perpendicular to radius
        letterMesh.rotation.z = -angle;

        textGroup.add(letterMesh);
        charIndex++;
    }

    // Rotate the entire text group 90 degrees around X axis
    textGroup.rotation.x = -Math.PI / 2;
    
    // Position the text group at the correct height on the ring
    textGroup.position.y = ringHeight / 2 - 1.5;

    // Adjust text depth penetration
    textGroup.position.z = -0.2;

    return textGroup;
}

// Combine ring and text - simplified version
function combineRingAndText(ring, textGroup, ringSize) {
    // Create final combined group
    const combinedGroup = new THREE.Group();
    
    // Add ring
    combinedGroup.add(ring.clone());
    
    // Add text group
    combinedGroup.add(textGroup);

    return combinedGroup;
}

// Update the updateRing function to use new parameters
function updateRing() {
    const text = document.getElementById('textInput').value || 'LOVE';
    const fontName = document.getElementById('fontSelect').value;
    const ringSize = document.getElementById('ringSize').value;
    const letterSpacing = parseFloat(document.getElementById('letterSpacing').value);
    const maxArc = parseFloat(document.getElementById('maxArc').value);

    if (!fonts[fontName]) {
        document.getElementById('status').textContent = 'Loading fonts...';
        return;
    }

    document.getElementById('status').textContent = 'Generating...';

    // Clear previous meshes
    if (finalMesh) {
        scene.remove(finalMesh);
    }

    // Create ring
    ringMesh = createRing(ringSize);

    // Create curved text with user-controlled parameters
    const textGroup = createCurvedText(text.toUpperCase(), fonts[fontName], ringSize, letterSpacing, maxArc);

    // Combine ring and text
    finalMesh = combineRingAndText(ringMesh, textGroup, ringSize);

    scene.add(finalMesh);

    document.getElementById('status').textContent = 'Ready';
}

// Export to STL
function exportSTL() {
    if (!finalMesh) {
        alert('Please generate a ring first');
        return;
    }
    
    const exporter = new THREE.STLExporter();
    const stlString = exporter.parse(finalMesh);
    
    const blob = new Blob([stlString], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `ring_${document.getElementById('textInput').value}_${document.getElementById('ringSize').value}.stl`;
    link.click();
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
