// constants.js

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

// Lighting presets
const LIGHTING_PRESETS = {
    studio: {
        name: 'Studio',
        ambient: { intensity: 0.8, color: 0xffffff },
        directional: { intensity: 0.5, color: 0xffffff, position: [10, 10, 5] },
        fill: { intensity: 0.5, color: 0xffffff, position: [-5, 5, -5] },
        hemisphere: { intensity: 0.3, skyColor: 0xffffff, groundColor: 0x444444 },
        toneMappingExposure: 1.5,
        environment: 0xffffff
    },
    bright: {
        name: 'Bright',
        ambient: { intensity: 1.2, color: 0xffffff },
        directional: { intensity: 1.5, color: 0xffffff, position: [10, 10, 5] },
        fill: { intensity: 0.8, color: 0xffffff, position: [-5, 5, -5] },
        hemisphere: { intensity: 0.5, skyColor: 0xffffff, groundColor: 0x666666 },
        toneMappingExposure: 2.0,
        environment: 0xffffff
    },
    soft: {
        name: 'Soft',
        ambient: { intensity: 0.6, color: 0xfff5e6 },
        directional: { intensity: 0.3, color: 0xfff5e6, position: [8, 8, 8] },
        fill: { intensity: 0.3, color: 0xfff5e6, position: [-8, 4, -8] },
        hemisphere: { intensity: 0.2, skyColor: 0xfff5e6, groundColor: 0x333333 },
        toneMappingExposure: 1.2,
        environment: 0xfff5e6
    },
    dramatic: {
        name: 'Dramatic',
        ambient: { intensity: 0.2, color: 0xffffff },
        directional: { intensity: 1.8, color: 0xffffff, position: [15, 15, 0] },
        fill: { intensity: 0.1, color: 0x4444ff, position: [-10, 0, -10] },
        hemisphere: { intensity: 0.1, skyColor: 0xffffff, groundColor: 0x000000 },
        toneMappingExposure: 1.8,
        environment: 0x222222
    },
    natural: {
        name: 'Natural',
        ambient: { intensity: 0.7, color: 0xffffcc },
        directional: { intensity: 0.8, color: 0xffffcc, position: [12, 12, 8] },
        fill: { intensity: 0.4, color: 0xccddff, position: [-8, 6, -6] },
        hemisphere: { intensity: 0.4, skyColor: 0xccddff, groundColor: 0x665544 },
        toneMappingExposure: 1.4,
        environment: 0xeeeedd
    },
    warm: {
        name: 'Warm',
        ambient: { intensity: 0.5, color: 0xffcc99 },
        directional: { intensity: 0.7, color: 0xffaa66, position: [10, 8, 6] },
        fill: { intensity: 0.4, color: 0xff9966, position: [-6, 4, -8] },
        hemisphere: { intensity: 0.3, skyColor: 0xffcc99, groundColor: 0x663333 },
        toneMappingExposure: 1.6,
        environment: 0xffcc99
    }
};

// Debouncing configuration
const DEBOUNCE_DELAY = 300; // milliseconds
