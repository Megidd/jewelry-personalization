// lighting.js

// Lighting objects
let lights = {
    ambient: null,
    directional: null,
    fill: null,
    hemisphere: null,
    spot: null
};

// Current lighting preset
let currentLightingPreset = 'studio';

// Initialize lighting objects
function initializeLighting() {
    // Ambient light
    lights.ambient = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(lights.ambient);

    // Main directional light
    lights.directional = new THREE.DirectionalLight(0xffffff, 0.5);
    lights.directional.position.set(10, 10, 5);
    lights.directional.castShadow = true;
    lights.directional.shadow.camera.near = 0.1;
    lights.directional.shadow.camera.far = 100;
    lights.directional.shadow.camera.left = -30;
    lights.directional.shadow.camera.right = 30;
    lights.directional.shadow.camera.top = 30;
    lights.directional.shadow.camera.bottom = -30;
    lights.directional.shadow.mapSize.width = 2048;
    lights.directional.shadow.mapSize.height = 2048;
    scene.add(lights.directional);

    // Fill light
    lights.fill = new THREE.DirectionalLight(0xffffff, 0.5);
    lights.fill.position.set(-5, 5, -5);
    scene.add(lights.fill);

    // Hemisphere light
    lights.hemisphere = new THREE.HemisphereLight(0xffffff, 0x444444, 0.3);
    scene.add(lights.hemisphere);

    // Spot light (initially disabled)
    lights.spot = new THREE.SpotLight(0xffffff, 0);
    lights.spot.position.set(0, 20, 0);
    lights.spot.angle = Math.PI / 6;
    lights.spot.penumbra = 0.1;
    lights.spot.decay = 2;
    lights.spot.distance = 100;
    lights.spot.castShadow = true;
    scene.add(lights.spot);
}

// Apply lighting preset
function applyLightingPreset(presetName) {
    const preset = LIGHTING_PRESETS[presetName];
    if (!preset) return;

    // Update ambient light
    lights.ambient.intensity = preset.ambient.intensity;
    lights.ambient.color.setHex(preset.ambient.color);

    // Update directional light
    lights.directional.intensity = preset.directional.intensity;
    lights.directional.color.setHex(preset.directional.color);
    lights.directional.position.set(...preset.directional.position);

    // Update fill light
    lights.fill.intensity = preset.fill.intensity;
    lights.fill.color.setHex(preset.fill.color);
    lights.fill.position.set(...preset.fill.position);

    // Update hemisphere light
    lights.hemisphere.intensity = preset.hemisphere.intensity;
    lights.hemisphere.color.setHex(preset.hemisphere.skyColor);
    lights.hemisphere.groundColor.setHex(preset.hemisphere.groundColor);

    // Update tone mapping
    renderer.toneMappingExposure = preset.toneMappingExposure;

    // Update environment
    scene.environment = new THREE.Color(preset.environment);

    // Special effects for certain presets
    if (presetName === 'dramatic') {
        lights.spot.intensity = 2.0;
        lights.spot.color.setHex(0xffffff);
    } else {
        lights.spot.intensity = 0;
    }

    currentLightingPreset = presetName;
}

// Set lighting preset (called from HTML)
function setLightingPreset(presetName) {
    // Update UI
    document.querySelectorAll('.lighting-preset').forEach(el => {
        el.classList.remove('active');
    });
    event.target.closest('.lighting-preset').classList.add('active');

    // Apply preset
    applyLightingPreset(presetName);
}
