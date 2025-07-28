# Usage Instructions

1. **Install the dependency**:

   ```bash
   npm install
   ```
   
2. **Place your TTF files** anywhere inside the `./fonts/` directory or its subdirectories

3. **Run the conversion script**:
   
   ```bash
   npm run convert-fonts
   or
   node convert-fonts.js
   ```

4. **The script will**:

- Search for all `.ttf` files in `./fonts/` and subdirectories
- Convert each TTF to Three.js JSON format
- Save JSON files in the `./fonts/` directory (root level) with the same name
