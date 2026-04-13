const API = "";

async function calculate() {
    const data = {
        age: document.getElementById("age").value,
        duration: document.getElementById("duration").value,
        disabled: document.getElementById("disabled").checked
    };

    const res = await fetch(API + "/calculate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    const result = await res.json();

    // UPDATED: Now uses € instead of lv.
    document.getElementById("price").innerText =
        "Price: " + result.price + " €";
}

async function buy() {
    const priceText = document.getElementById("price").innerText;

    if (!priceText) {
        alert("Calculate price first!");
        return;
    }

    // UPDATED: Strip the € symbol before sending to the backend
    const price = priceText
        .replace("Price: ", "")
        .replace(" €", "");

    const res = await fetch(API + "/buy", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ price: price })
    });

    const result = await res.json();

    // Grab the result div
    const resultDiv = document.getElementById("ticketResult");

    // UPDATED: Ticket now displays € instead of lv.
    resultDiv.innerHTML = `
        <div class="ticket-header">🎟️ Official IARA Permit</div>
        <div class="ticket-detail"><strong>Permit ID:</strong> ${result.ticket_id}</div>
        <div class="ticket-detail"><strong>Type:</strong> Amateur Fishing</div>
        <div class="ticket-detail"><strong>Paid:</strong> ${result.price} €</div>
        <div class="ticket-detail" style="margin-top: 15px; font-size: 12px; color: #a1c6ea;">
            Keep this digital pass ready for inspection.
        </div>
    `;

    // Make the div visible (since it starts hidden via the CSS we added earlier)
    resultDiv.style.display = "block";
}