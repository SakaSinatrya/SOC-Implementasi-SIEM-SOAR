<?php
// Skrip rentan untuk keperluan PoC
if(isset($_FILES['file'])) {
    $target_path = "/var/www/html/" . basename($_FILES['file']['name']);
    move_uploaded_file($_FILES['file']['tmp_name'], $target_path);
    echo "Sukses upload ke: " . $target_path;
}
?>
