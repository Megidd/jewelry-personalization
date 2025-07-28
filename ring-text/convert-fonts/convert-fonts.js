const fs = require('fs');
const path = require('path');
const opentype = require('opentype.js');

// Reverse commands function (exact copy from original)
function reverseCommands(commands) {
    var paths = [];
    var path;
    
    commands.forEach(function(c) {
        if (c.type.toLowerCase() === "m") {
            path = [c];
            paths.push(path);
        } else if (c.type.toLowerCase() !== "z") {
            path.push(c);
        }
    });
    
    var reversed = [];
    paths.forEach(function(p) {
        var result = {"type": "m", "x": p[p.length-1].x, "y": p[p.length-1].y};
        reversed.push(result);
        
        for(var i = p.length - 1; i > 0; i--) {
            var command = p[i];
            result = {"type": command.type};
            if (command.x2 !== undefined && command.y2 !== undefined) {
                result.x1 = command.x2;
                result.y1 = command.y2;
                result.x2 = command.x1;
                result.y2 = command.y1;
            } else if (command.x1 !== undefined && command.y1 !== undefined) {
                result.x1 = command.x1;
                result.y1 = command.y1;
            }
            result.x = p[i-1].x;
            result.y = p[i-1].y;
            reversed.push(result);
        }
    });
    
    return reversed;
}

// Convert function (exact logic from original)
function convert(font, options = {}) {
    console.log(`Converting font: ${font.names.fontFamily.en || 'Unknown'} ${font.names.fontSubfamily.en || ''}`);
    
    var scale = (1000 * 100) / ((font.unitsPerEm || 2048) * 72);
    var result = {};
    result.glyphs = {};
    
    var restriction = {
        range: null,
        set: null
    };
    
    // Handle character restrictions if provided
    if (options.restrictCharacters && options.restrictCharacterSet) {
        var restrictContent = options.restrictCharacterSet;
        var rangeSeparator = '-';
        if (restrictContent.indexOf(rangeSeparator) != -1) {
            var rangeParts = restrictContent.split(rangeSeparator);
            if (rangeParts.length === 2 && !isNaN(rangeParts[0]) && !isNaN(rangeParts[1])) {
                restriction.range = [parseInt(rangeParts[0]), parseInt(rangeParts[1])];
            }
        }
        if (restriction.range === null) {
            restriction.set = restrictContent;
        }
    }
    
    // In opentype.js, we need to iterate through the glyphs using the length property
    var numGlyphs = font.numGlyphs || font.glyphs.length;
    
    for (var i = 0; i < numGlyphs; i++) {
        var glyph = font.glyphs.get(i);
        if (!glyph) continue;
        
        const unicodes = [];
        if (glyph.unicode !== undefined) {
            unicodes.push(glyph.unicode);
        }
        if (glyph.unicodes && glyph.unicodes.length) {
            glyph.unicodes.forEach(function(unicode) {
                if (unicodes.indexOf(unicode) == -1) {
                    unicodes.push(unicode);
                }
            });
        }
        
        unicodes.forEach(function(unicode) {
            var glyphCharacter = String.fromCharCode(unicode);
            var needToExport = true;
            if (restriction.range !== null) {
                needToExport = (unicode >= restriction.range[0] && unicode <= restriction.range[1]);
            } else if (restriction.set !== null) {
                needToExport = (restriction.set.indexOf(glyphCharacter) != -1);
            }
            if (needToExport) {
                var token = {};
                token.ha = Math.round(glyph.advanceWidth * scale);
                token.x_min = Math.round(glyph.xMin * scale);
                token.x_max = Math.round(glyph.xMax * scale);
                token.o = "";
                
                // Get the path for this glyph
                var glyphPath = glyph.getPath(0, 0, font.unitsPerEm);
                var commands = glyphPath.commands;
                
                if (options.reverseTypeface) {
                    commands = reverseCommands(commands);
                }
                
                commands.forEach(function(command, i) {
                    if (command.type.toLowerCase() === "c") {
                        command.type = "b";
                    }
                    token.o += command.type.toLowerCase();
                    token.o += " ";
                    if (command.x !== undefined && command.y !== undefined) {
                        token.o += Math.round(command.x * scale);
                        token.o += " ";
                        token.o += Math.round(command.y * scale);
                        token.o += " ";
                    }
                    if (command.x1 !== undefined && command.y1 !== undefined) {
                        token.o += Math.round(command.x1 * scale);
                        token.o += " ";
                        token.o += Math.round(command.y1 * scale);
                        token.o += " ";
                    }
                    if (command.x2 !== undefined && command.y2 !== undefined) {
                        token.o += Math.round(command.x2 * scale);
                        token.o += " ";
                        token.o += Math.round(command.y2 * scale);
                        token.o += " ";
                    }
                });
                result.glyphs[String.fromCharCode(unicode)] = token;
            }
        });
    }
    
    result.familyName = font.names.fontFamily.en || font.names.fontFamily || '';
    result.ascender = Math.round(font.ascender * scale);
    result.descender = Math.round(font.descender * scale);
    result.underlinePosition = font.tables.post ? Math.round(font.tables.post.underlinePosition * scale) : 0;
    result.underlineThickness = font.tables.post ? Math.round(font.tables.post.underlineThickness * scale) : 0;
    result.boundingBox = {
        "yMin": Math.round(font.tables.head.yMin * scale),
        "xMin": Math.round(font.tables.head.xMin * scale),
        "yMax": Math.round(font.tables.head.yMax * scale),
        "xMax": Math.round(font.tables.head.xMax * scale)
    };
    result.resolution = 1000;
    result.original_font_information = font.tables.name;
    
    // Get style name for CSS properties
    var styleName = (font.names.fontSubfamily && font.names.fontSubfamily.en) || '';
    
    if (styleName.toLowerCase().indexOf("bold") > -1) {
        result.cssFontWeight = "bold";
    } else {
        result.cssFontWeight = "normal";
    }
    
    if (styleName.toLowerCase().indexOf("italic") > -1) {
        result.cssFontStyle = "italic";
    } else {
        result.cssFontStyle = "normal";
    }
    
    return result;
}

// Convert TTF to Three.js JSON format
function convertTTFtoJSON(ttfPath, outputPath, options = {}) {
    try {
        console.log(`Processing: ${ttfPath}`);
        
        // Load the font
        const font = opentype.loadSync(ttfPath);
        
        // Convert using the exact same logic as the original
        const result = convert(font, options);
        
        // Write the JSON file
        let output;
        if (options.outputFormat === 'js') {
            output = `if (_typeface_js && _typeface_js.loadFace) _typeface_js.loadFace(${JSON.stringify(result)});`;
        } else {
            output = JSON.stringify(result, null, 2);
        }
        
        fs.writeFileSync(outputPath, output);
        console.log(`✓ Converted: ${path.basename(outputPath)}`);
        
        // Debug info
        const glyphCount = Object.keys(result.glyphs).length;
        console.log(`  Total glyphs: ${glyphCount}`);
        const sampleChars = Object.keys(result.glyphs).slice(0, 20);
        console.log(`  Sample characters: ${sampleChars.join('')}`);
        console.log(`  Has 'L'? ${result.glyphs['L'] ? 'Yes' : 'No'}`);
        
        return true;
    } catch (error) {
        console.error(`✗ Error converting ${ttfPath}:`, error);
        console.error(error.stack);
        return false;
    }
}

// Recursively find all TTF files in a directory
function findTTFFiles(dir, fileList = []) {
    const files = fs.readdirSync(dir);
    
    files.forEach(file => {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);
        
        if (stat.isDirectory()) {
            findTTFFiles(filePath, fileList);
        } else if (file.toLowerCase().endsWith('.ttf')) {
            fileList.push(filePath);
        }
    });
    
    return fileList;
}

// Main conversion function
function convertAllFonts(options = {}) {
    const fontsDir = './fonts';
    
    console.log('🔍 Searching for TTF files...\n');
    
    // Find all TTF files
    const ttfFiles = findTTFFiles(fontsDir);
    
    if (ttfFiles.length === 0) {
        console.log('No TTF files found in the fonts directory.');
        return;
    }
    
    console.log(`Found ${ttfFiles.length} TTF file(s):\n`);
    
    let successCount = 0;
    let failCount = 0;
    
    // Convert each TTF file
    ttfFiles.forEach(ttfPath => {
        // Create output path: same location, but with .json extension
        const dir = path.dirname(ttfPath);
        const baseName = path.basename(ttfPath, '.ttf');
        const extension = options.outputFormat === 'js' ? '.js' : '.json';
        const jsonPath = path.join(fontsDir, `${baseName}${extension}`);
        
        if (convertTTFtoJSON(ttfPath, jsonPath, options)) {
            successCount++;
        } else {
            failCount++;
        }
    });
    
    console.log('\n📊 Conversion Summary:');
    console.log(`✓ Successfully converted: ${successCount} font(s)`);
    if (failCount > 0) {
        console.log(`✗ Failed to convert: ${failCount} font(s)`);
    }
}

// Check if opentype.js is installed
try {
    require.resolve('opentype.js');
} catch (e) {
    console.error('❌ opentype.js is not installed!');
    console.log('Please run: npm install opentype.js');
    process.exit(1);
}

// Configuration options (you can modify these)
const conversionOptions = {
    reverseTypeface: false,              // Set to true to reverse paths
    restrictCharacters: false,           // Set to true to restrict character set
    restrictCharacterSet: "",            // e.g., "A-Z" or "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    outputFormat: 'json'                 // 'json' or 'js'
};

// Run the conversion
console.log('🚀 Three.js Font Converter (Original Algorithm)\n');
convertAllFonts(conversionOptions);
