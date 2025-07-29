function createCurvedTextWithData(text, font, customDimensions, letterSpacing) {
    const ringOuterRadius = customDimensions.innerRadius + customDimensions.thickness;
    const textSize = customDimensions.textSize;
    const textDepth = customDimensions.textDepth;

    // Array to hold all letter geometries
    const letterGeometries = [];
    
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

    // First pass: measure all characters and calculate their widths
    const charData = [];
    let totalWidth = 0;
    
    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        if (char === ' ') continue;
        
        // Create temporary geometry to measure
        const tempGeometry = new THREE.TextGeometry(char, {
            font: font,
            size: textSize,
            height: textDepth,
            curveSegments: 12,
            bevelEnabled: true,
            bevelThickness: 0.03,
            bevelSize: 0.03,
            bevelSegments: 3
        });
        
        tempGeometry.computeBoundingBox();
        const bbox = tempGeometry.boundingBox;
        const width = bbox.max.x - bbox.min.x;
        
        charData.push({
            char: char,
            width: width,
            geometry: tempGeometry,
            bbox: bbox
        });
        
        totalWidth += width;
    }
    
    // Calculate spacing between characters
    const spacingWidth = textSize * 0.2 * letterSpacing;
    const totalSpacingWidth = spacingWidth * Math.max(0, charCount - 1);
    const totalArcLength = totalWidth + totalSpacingWidth;
    
    // Convert arc length to angle
    const totalAngle = totalArcLength / ringOuterRadius;
    
    // Start from left side and go right
    const startAngle = totalAngle / 2 + Math.PI / 2;
    
    // Track the actual angular extent of the text
    let currentAngle = startAngle;
    let minAngle = startAngle;
    let maxAngle = startAngle - totalAngle;

    // Second pass: position characters based on their actual widths
    for (let i = 0; i < charData.length; i++) {
        const data = charData[i];
        const geometry = data.geometry;
        const bbox = data.bbox;
        
        // Center the letter
        const centerX = (bbox.max.x - bbox.min.x) / 2;
        const centerY = (bbox.max.y - bbox.min.y) / 2;
        const letterHeight = bbox.max.y - bbox.min.y;
        
        // Center the letter geometry in X and Y, but not Z
        geometry.translate(-centerX, -centerY, 0);
        
        // Calculate angle for this specific character based on its width
        const charWidthAngle = data.width / ringOuterRadius;
        const charAngle = currentAngle - charWidthAngle / 2;
        
        // Create transformation matrix
        const matrix = new THREE.Matrix4();
        
        // Position at ring's outer radius
        const radius = ringOuterRadius;
        
        // Position in X-Y plane (ring is along Z axis)
        const x = Math.cos(charAngle) * radius;
        const y = Math.sin(charAngle) * radius;
        const z = 0;
        
        // Apply rotations in correct order
        const flipX = new THREE.Matrix4().makeRotationX(Math.PI);
        matrix.multiply(flipX);
        
        const flipY = new THREE.Matrix4().makeRotationY(Math.PI);
        matrix.multiply(flipY);
        
        const rotationZ = charAngle + Math.PI / 2;
        const rotZ = new THREE.Matrix4().makeRotationZ(rotationZ);
        matrix.multiply(rotZ);
        
        matrix.setPosition(x, y, z);
        
        // Apply matrix to geometry
        geometry.applyMatrix4(matrix);
        
        // Move outward
        const normalX = Math.cos(charAngle);
        const normalY = Math.sin(charAngle);
        
        const outwardOffset = (letterHeight / 2) + 0.1;
        geometry.translate(normalX * outwardOffset, normalY * outwardOffset, 0);
        
        letterGeometries.push(geometry);
        
        // Update angle for next character
        currentAngle -= charWidthAngle + (spacingWidth / ringOuterRadius);
    }

    // Merge all letter geometries
    let mergedGeometry;
    if (letterGeometries.length > 0) {
        mergedGeometry = THREE.BufferGeometryUtils.mergeBufferGeometries(letterGeometries);
    } else {
        mergedGeometry = new THREE.BufferGeometry();
    }

    const selectedColor = document.querySelector('input[name="metalColor"]:checked').value;
    const material = new THREE.MeshStandardMaterial({
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

function createCurvedTextSleeping(text, font, customDimensions, letterSpacing) {
    const ringOuterRadius = customDimensions.innerRadius + customDimensions.thickness;
    const ringInnerRadius = customDimensions.innerRadius;
    const ringMidRadius = (ringOuterRadius + ringInnerRadius) / 2;
    const textSize = customDimensions.textSize;
    const textDepth = customDimensions.textDepth;

    // Array to hold all letter geometries
    const letterGeometries = [];

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

    // First pass: measure all characters and calculate their widths
    const charData = [];
    let totalWidth = 0;
    
    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        if (char === ' ') continue;
        
        // Create temporary geometry to measure
        const tempGeometry = new THREE.TextGeometry(char, {
            font: font,
            size: textSize,
            height: textDepth,
            curveSegments: 12,
            bevelEnabled: true,
            bevelThickness: 0.02,
            bevelSize: 0.02,
            bevelSegments: 3
        });
        
        tempGeometry.computeBoundingBox();
        const bbox = tempGeometry.boundingBox;
        const width = bbox.max.x - bbox.min.x;
        
        charData.push({
            char: char,
            width: width,
            geometry: tempGeometry,
            bbox: bbox
        });
        
        totalWidth += width;
    }
    
    // Calculate spacing between characters
    const spacingWidth = textSize * 0.25 * letterSpacing;
    const totalSpacingWidth = spacingWidth * Math.max(0, charCount - 1);
    const totalArcLength = totalWidth + totalSpacingWidth;
    
    // Convert arc length to angle using middle radius
    const totalAngle = totalArcLength / ringMidRadius;
    
    // For sleeping text at the TOP of the ring when viewed from the side
    const centerAngle = Math.PI / 2; // Top of the ring
    const startAngle = centerAngle + totalAngle / 2;

    // Track current position
    let currentAngle = startAngle;

    // Second pass: position characters based on their actual widths
    for (let i = 0; i < charData.length; i++) {
        const data = charData[i];
        const geometry = data.geometry;
        const bbox = data.bbox;
        
        // Center the letter
        const centerX = (bbox.max.x - bbox.min.x) / 2;
        const centerY = (bbox.max.y - bbox.min.y) / 2;
        const centerZ = (bbox.max.z - bbox.min.z) / 2;
        
        // Get the letter dimensions
        const letterWidth = bbox.max.x - bbox.min.x;
        const letterHeight = bbox.max.y - bbox.min.y;
        const letterDepth = bbox.max.z - bbox.min.z;

        // Center the letter geometry
        geometry.translate(-centerX, -centerY, -centerZ);

        // Calculate angle for this specific character based on its width
        const charWidthAngle = data.width / ringMidRadius;
        const charAngle = currentAngle - charWidthAngle / 2;

        // Create transformation matrix
        const matrix = new THREE.Matrix4();
        
        // Reset matrix
        matrix.identity();
        
        // First, position at origin and apply the flat rotation
        const flatRotation = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
        matrix.multiply(flatRotation);
        
        // Then apply the tangent rotation (around world Z axis)
        const tangentAngle = charAngle - Math.PI / 2;
        const tangentRotation = new THREE.Matrix4().makeRotationZ(tangentAngle);
        matrix.premultiply(tangentRotation); // premultiply to apply in world space
        
        // Calculate position on the ring
        const x = Math.cos(charAngle) * ringMidRadius;
        const y = Math.sin(charAngle) * ringMidRadius;
        const z = 0;
        
        // Finally, translate to the correct position
        matrix.setPosition(x, y, z);
        
        // Apply matrix to geometry
        geometry.applyMatrix4(matrix);
        
        letterGeometries.push(geometry);
        
        // Update angle for next character
        currentAngle -= charWidthAngle + (spacingWidth / ringMidRadius);
    }

    // Merge all letter geometries
    let mergedGeometry;
    if (letterGeometries.length > 0) {
        mergedGeometry = THREE.BufferGeometryUtils.mergeBufferGeometries(letterGeometries);
    } else {
        mergedGeometry = new THREE.BufferGeometry();
    }

    const selectedColor = document.querySelector('input[name="metalColor"]:checked').value;
    const material = new THREE.MeshStandardMaterial({
        color: METAL_COLORS[selectedColor],
        metalness: 0.8,
        roughness: 0.2
    });

    // Add some padding to the angular extent
    const angularPadding = 0.15; // radians
    
    // Handle wrapping around if angle goes beyond 2π
    let finalStartAngle = currentAngle - angularPadding;
    let finalEndAngle = startAngle + angularPadding;
    
    return {
        mesh: new THREE.Mesh(mergedGeometry, material),
        startAngle: finalStartAngle,
        endAngle: finalEndAngle,
        totalAngle: totalAngle + 2 * angularPadding
    };
}
