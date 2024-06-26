function fetchAddressSuggestions() {
    let addressInput = document.getElementById('address_line1').value;

    if (addressInput.length > 3) {
        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${addressInput}`)
            .then(response => response.json())
            .then(data => {
                let suggestions = data.slice(0, 5); // Take top 5 suggestions
                let suggestionsList = document.getElementById('addressSuggestions');
                suggestionsList.innerHTML = ''; // Clear existing suggestions

                suggestions.forEach(suggestion => {
                    let option = document.createElement('option');
                    option.value = suggestion.display_name;
                    suggestionsList.appendChild(option);
                });
            });
    }
}

document.getElementById('address_line1').addEventListener('input', function () {
    let addressInput = this.value;
    let suggestionsList = document.getElementById('addressSuggestions');

    for (let i = 0; i < suggestionsList.options.length; i++) {
        if (suggestionsList.options[i].value === addressInput) {
            fillInAddress(addressInput);
            break;
        }
    }
});

function fillInAddress(selectedAddress) {
    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${selectedAddress}&limit=1&addressdetails=1`)
        .then(response => response.json())
        .then(data => {
            if (data.length > 0) {
                let details = data[0];
                console.log(details);

                // Accessing individual components of the address
                let address = details.address;
                let city = address.city || address.town || address.village || '';
                let state = address.state || address.state_district || '';
                let postcode = address.postcode || '';
                let country = address.country || '';

                document.getElementById('city').value = city;
                document.getElementById('state').value = state;
                document.getElementById('zip_code').value = postcode;
                document.getElementById('country').value = country;
            }
        }).catch(error => {
        console.error(_l('Error fetching address data:'), error);
    });
}