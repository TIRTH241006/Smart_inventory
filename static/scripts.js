const API = "http://127.0.0.1:8000/api";

// Load Inventory
function loadProducts() {
    fetch(`${API}/products/`)
        .then(res => res.json())
        .then(data => {
            let table = document.getElementById("inventoryTable");
            table.innerHTML = "";

            data.forEach(p => {
                table.innerHTML += `
                    <tr>
                        <td>${p.name}</td>
                        <td>${p.quantity}</td>
                        <td>${p.price}</td>
                    </tr>
                `;
            });
        });
}

// Add Product
function addProduct() {
    let product = {
        name: document.getElementById("name").value,
        category: document.getElementById("category").value,
        quantity: parseInt(document.getElementById("quantity").value),
        price: parseFloat(document.getElementById("price").value),
        reorder_level: parseInt(document.getElementById("reorder").value)
    };

    fetch(`${API}/products/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(product)
    })
    .then(() => {
        loadProducts();
        loadLowStock();
    });
}

// Load Low Stock
function loadLowStock() {
    fetch("http://127.0.0.1:8000/api/low-stock/")
        .then(res => res.json())
        .then(data => {
            let list = document.getElementById("lowStockList");
            list.innerHTML = "";

            data.forEach(p => {
                list.innerHTML += `<li>${p.name} (Qty: ${p.quantity})</li>`;
            });
        });
}

// Initial Load
loadProducts();
loadLowStock();