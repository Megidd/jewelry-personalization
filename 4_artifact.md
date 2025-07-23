# WooCommerce 3D Model Platform Setup Guide

## Server Setup (Ubuntu 22.04.5 LTS)

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install LAMP Stack
```bash
# Install Apache
sudo apt install apache2 -y
sudo systemctl enable apache2

# Install MySQL
sudo apt install mysql-server -y
sudo mysql_secure_installation

# Install PHP and required extensions
sudo apt install php php-mysql php-curl php-gd php-mbstring php-xml php-xmlrpc php-soap php-intl php-zip php-imagick libapache2-mod-php -y

# Enable Apache modules
sudo a2enmod rewrite
sudo systemctl restart apache2
```

### 3. Configure MySQL Database
```bash
sudo mysql -u root -p
```
```sql
CREATE DATABASE woocommerce_3d;
CREATE USER 'woo_user'@'localhost' IDENTIFIED BY 'strong_password_here';
GRANT ALL PRIVILEGES ON woocommerce_3d.* TO 'woo_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. Install WordPress
```bash
cd /tmp
wget https://wordpress.org/latest.tar.gz
tar xzvf latest.tar.gz
sudo cp -R wordpress/* /var/www/html/
sudo chown -R www-data:www-data /var/www/html/
sudo chmod -R 755 /var/www/html/
```

### 5. Configure Apache for Domain
Create virtual host file:
```bash
sudo nano /etc/apache2/sites-available/facegold.com.conf
```

Add configuration:
```apache
<VirtualHost *:80>
    ServerName facegold.com
    ServerAlias www.facegold.com
    DocumentRoot /var/www/html
    
    <Directory /var/www/html>
        AllowOverride All
        Require all granted
    </Directory>
    
    ErrorLog ${APACHE_LOG_DIR}/facegold_error.log
    CustomLog ${APACHE_LOG_DIR}/facegold_access.log combined
</VirtualHost>
```

Enable the site:
```bash
sudo a2ensite facegold.com.conf
sudo a2dissite 000-default.conf
sudo systemctl reload apache2
```

### 6. Install SSL Certificate (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-apache -y
sudo certbot --apache -d facegold.com -d www.facegold.com
```

### 7. Configure WordPress
Create wp-config.php:
```bash
sudo cp /var/www/html/wp-config-sample.php /var/www/html/wp-config.php
sudo nano /var/www/html/wp-config.php
```

Update database settings:
```php
define('DB_NAME', 'woocommerce_3d');
define('DB_USER', 'woo_user');
define('DB_PASSWORD', 'strong_password_here');
define('DB_HOST', 'localhost');
```

## WooCommerce Installation

### 1. Install WooCommerce Plugin
- Access WordPress admin at `https://facegold.com/wp-admin`
- Go to Plugins > Add New
- Search for "WooCommerce"
- Install and activate

### 2. Install Required Plugins
Install these additional plugins:
- **WP File Upload** (for image uploads)
- **Custom Product Tabs for WooCommerce**
- **WooCommerce Customizer**

## Custom 3D Model Product Setup

### 1. Create Custom Product Type
Add to your theme's `functions.php`:

```php
// Add custom product type
add_filter('product_type_selector', 'add_3d_model_product_type');
function add_3d_model_product_type($types) {
    $types['3d_model'] = '3D Model Generator';
    return $types;
}

// Handle file uploads
add_action('wp_ajax_upload_image_for_3d', 'handle_3d_image_upload');
add_action('wp_ajax_nopriv_upload_image_for_3d', 'handle_3d_image_upload');

function handle_3d_image_upload() {
    if (!wp_verify_nonce($_POST['nonce'], '3d_upload_nonce')) {
        wp_die('Security check failed');
    }
    
    $uploaded_file = $_FILES['image'];
    $upload_dir = wp_upload_dir();
    
    // Validate file type
    $allowed_types = array('image/jpeg', 'image/png', 'image/jpg');
    if (!in_array($uploaded_file['type'], $allowed_types)) {
        wp_send_json_error('Invalid file type');
    }
    
    // Process upload
    $file_path = $upload_dir['path'] . '/' . $uploaded_file['name'];
    move_uploaded_file($uploaded_file['tmp_name'], $file_path);
    
    // Generate placeholder 3D model
    $ply_content = generate_placeholder_ply();
    $ply_filename = 'model_' . time() . '.ply';
    $ply_path = $upload_dir['path'] . '/' . $ply_filename;
    file_put_contents($ply_path, $ply_content);
    
    wp_send_json_success(array(
        'model_url' => $upload_dir['url'] . '/' . $ply_filename,
        'model_path' => $ply_path
    ));
}

function generate_placeholder_ply() {
    return "ply
format ascii 1.0
element vertex 8
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
element face 12
property list uchar int vertex_indices
end_header
-1.0 -1.0 -1.0 255 0 0
1.0 -1.0 -1.0 0 255 0
1.0 1.0 -1.0 0 0 255
-1.0 1.0 -1.0 255 255 0
-1.0 -1.0 1.0 255 0 255
1.0 -1.0 1.0 0 255 255
1.0 1.0 1.0 128 128 128
-1.0 1.0 1.0 255 128 0
3 0 1 2
3 0 2 3
3 4 7 6
3 4 6 5
3 0 4 5
3 0 5 1
3 2 6 7
3 2 7 3
3 0 3 7
3 0 7 4
3 1 5 6
3 1 6 2";
}
```

### 2. Create Custom Product Page Template
Create `single-product-3d-model.php` in your theme:

```php
<?php
get_header();
?>

<div class="container">
    <div class="row">
        <div class="col-md-6">
            <h2>Upload Image for 3D Model Generation</h2>
            <form id="3d-upload-form" enctype="multipart/form-data">
                <input type="file" id="image-upload" name="image" accept="image/*" required>
                <button type="submit">Generate 3D Model</button>
                <?php wp_nonce_field('3d_upload_nonce', 'nonce'); ?>
            </form>
            <div id="upload-status"></div>
        </div>
        <div class="col-md-6">
            <div id="3d-preview">
                <h3>3D Model Preview</h3>
                <div id="model-viewer"></div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
let scene, camera, renderer, model;

function init3DViewer() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, 400/400, 0.1, 1000);
    renderer = new THREE.WebGLRenderer();
    renderer.setSize(400, 400);
    document.getElementById('model-viewer').appendChild(renderer.domElement);
    
    camera.position.z = 5;
    
    // Add lighting
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(0, 1, 1);
    scene.add(light);
    
    const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
    scene.add(ambientLight);
    
    animate();
}

function animate() {
    requestAnimationFrame(animate);
    if (model) {
        model.rotation.x += 0.01;
        model.rotation.y += 0.01;
    }
    renderer.render(scene, camera);
}

function loadPLYModel(url) {
    fetch(url)
        .then(response => response.text())
        .then(plyData => {
            const geometry = parsePLY(plyData);
            const material = new THREE.MeshLambertMaterial({vertexColors: true});
            
            if (model) scene.remove(model);
            model = new THREE.Mesh(geometry, material);
            scene.add(model);
        });
}

function parsePLY(plyData) {
    const lines = plyData.split('\n');
    const vertices = [];
    const colors = [];
    const faces = [];
    
    let vertexCount = 0;
    let faceCount = 0;
    let readingVertices = false;
    let readingFaces = false;
    
    for (let line of lines) {
        if (line.includes('element vertex')) {
            vertexCount = parseInt(line.split(' ')[2]);
        } else if (line.includes('element face')) {
            faceCount = parseInt(line.split(' ')[2]);
        } else if (line === 'end_header') {
            readingVertices = true;
            continue;
        }
        
        if (readingVertices && vertexCount > 0) {
            const parts = line.split(' ');
            vertices.push(parseFloat(parts[0]), parseFloat(parts[1]), parseFloat(parts[2]));
            colors.push(parseInt(parts[3])/255, parseInt(parts[4])/255, parseInt(parts[5])/255);
            vertexCount--;
            if (vertexCount === 0) {
                readingVertices = false;
                readingFaces = true;
            }
        } else if (readingFaces && faceCount > 0) {
            const parts = line.split(' ');
            faces.push(parseInt(parts[1]), parseInt(parts[2]), parseInt(parts[3]));
            faceCount--;
        }
    }
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.setIndex(faces);
    geometry.computeVertexNormals();
    
    return geometry;
}

// Initialize viewer on page load
document.addEventListener('DOMContentLoaded', function() {
    init3DViewer();
    
    document.getElementById('3d-upload-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        formData.append('action', 'upload_image_for_3d');
        
        fetch(ajaxurl, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                document.getElementById('upload-status').innerHTML = 
                    '<p style="color: green;">3D model generated successfully!</p>';
                loadPLYModel(result.data.model_url);
            } else {
                document.getElementById('upload-status').innerHTML = 
                    '<p style="color: red;">Error: ' + result.data + '</p>';
            }
        })
        .catch(error => {
            document.getElementById('upload-status').innerHTML = 
                '<p style="color: red;">Upload failed: ' + error + '</p>';
        });
    });
});
</script>

<?php get_footer(); ?>
```

## Domain Configuration

### 1. DNS Setup
Point your domain to the server IP:
```
A record: facegold.com → YOUR_SERVER_IP
A record: www.facegold.com → YOUR_SERVER_IP
```

### 2. WordPress URL Configuration
In wp-config.php, add:
```php
define('WP_HOME','https://facegold.com');
define('WP_SITEURL','https://facegold.com');
```

## Security & Performance

### 1. Configure Firewall
```bash
sudo ufw enable
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
```

### 2. File Permissions
```bash
sudo chown -R www-data:www-data /var/www/html/
sudo find /var/www/html/ -type d -exec chmod 755 {} \;
sudo find /var/www/html/ -type f -exec chmod 644 {} \;
```

### 3. Upload Directory Permissions
```bash
sudo chmod 755 /var/www/html/wp-content/uploads/
```

## Testing

1. Access `https://facegold.com`
2. Create a 3D Model product
3. Test image upload functionality
4. Verify 3D model preview works
5. Check PLY file generation

## Sample PLY File Structure

The generated PLY files follow this format:
- Header with vertex/face counts
- Vertex data with coordinates and RGB colors
- Face data with vertex indices
- Creates a simple colored cube as placeholder

## Future Enhancements

To implement sophisticated 3D model generation:
1. Integrate with AI/ML services (like Meshy API or custom models)
2. Add photogrammetry processing
3. Implement advanced 3D reconstruction algorithms
4. Add texture mapping capabilities

This setup provides a complete WooCommerce platform with basic 3D model generation functionality that can be enhanced with advanced processing logic as needed.