// ring-geometry.js

let ringMesh, textMesh, finalMesh;

// Modified createRing function that uses custom dimensions
function createRing(customDimensions, startAngle = 0, endAngle = Math.PI * 2) {
    const innerRadius = customDimensions.innerRadius;
    const outerRadius = customDimensions.innerRadius + customDimensions.thickness;
    const height = customDimensions.height;

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
