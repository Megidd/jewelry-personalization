// ring-geometry.js
let ringMesh, textMesh, finalMesh;

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
    const material = new THREE.MeshStandardMaterial({
        color: METAL_COLORS[selectedColor],
        metalness: 0.8,
        roughness: 0.2
    });

    return new THREE.Mesh(ringGeometry, material);
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
    const material = new THREE.MeshStandardMaterial({
        color: METAL_COLORS[selectedColor],
        metalness: 0.8,
        roughness: 0.2
    });
    
    return new THREE.Mesh(mergedGeometry, material);
}
