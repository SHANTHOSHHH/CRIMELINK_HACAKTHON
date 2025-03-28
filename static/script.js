// Function to switch sections within the same page
function navigateSection(sectionId) {
    let pages = document.getElementsByClassName("page");

    // Hide all sections
    for (let i = 0; i < pages.length; i++) {
        pages[i].classList.add("hidden");
    }

    // Show the selected section
    let targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.remove("hidden");
    } else {
        console.error("Error: Section with ID", sectionId, "not found.");
    }
}

// Function to load a new Flask page
function navigateToPage(url) {
    window.location.href = url;
}

// Ensure sidebar links work correctly
document.addEventListener("DOMContentLoaded", function () {
    let navLinks = document.querySelectorAll(".sidebar a");

    navLinks.forEach(link => {
        link.addEventListener("click", function (event) {
            let sectionId = this.getAttribute("data-section");

            // If the section is within the same page, show it
            if (document.getElementById(sectionId)) {
                event.preventDefault();
                navigateSection(sectionId);
            } else {
                // Otherwise, load a new Flask page
                navigateToPage(this.href);
            }
        });
    });
});


// Send message to Flask backend and get response
// Send message to Flask backend and get response
function sendMessage() {
    let userInput = document.getElementById("userInput").value;
    if (!userInput.trim()) return;

    // Display user message
    let chatbox = document.getElementById("chatbox");
    let userMessage = document.createElement("div");
    userMessage.classList.add("chat-message", "user");
    userMessage.innerText = userInput;
    chatbox.appendChild(userMessage);

    // Send request to Flask backend
    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userInput })
    })
    .then(response => response.json())
    .then(data => {
        let botMessage = document.createElement("div");
        botMessage.classList.add("chat-message", "bot");

        // Check if response contains case details (object format)
        if (typeof data.response === "object") {
            botMessage.innerHTML = `<strong>Case Title:</strong> ${data.response["Case Title"]} <br>
                                    <strong>Suspect Name:</strong> ${data.response["Suspect Name"]} <br>
                                    <strong>Crime Type:</strong> ${data.response["Crime Type"]} <br>
                                    <strong>Status:</strong> ${data.response["Status"]} <br>
                                    <strong>FIR Number:</strong> ${data.response["FIR Number"]} <br>
                                    <strong>Details:</strong> ${data.response["Details"]}`;
        } else {
            // If the response is text (NLP-generated)
            botMessage.innerText = data.response;
        }

        chatbox.appendChild(botMessage);
        chatbox.scrollTop = chatbox.scrollHeight; // Auto-scroll to latest message
    })
    .catch(error => console.error("Error:", error));

    document.getElementById("userInput").value = ""; // Clear input field after sending
}


// Function to handle Enter key for sending messages
document.getElementById("userInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault(); // Prevents default new line action
        sendMessage(); // Calls the existing sendMessage() function
    }
});


// Dark mode toggle
function toggleDarkMode() {
    document.body.classList.toggle("dark-mode");
}
// Function to save user settings
function saveSettings() {
    let notifications = document.getElementById("notifications").checked;
    let soundAlerts = document.getElementById("soundAlerts").checked;
    let customStatus = document.getElementById("customStatus").value;

    alert("Settings Saved!\n\n" +
          "Notifications: " + (notifications ? "ON" : "OFF") + "\n" +
          "Sound Alerts: " + (soundAlerts ? "ON" : "OFF") + "\n" +
          "Custom Status: " + (customStatus || "None"));
}


// Function to preview image before uploading
function previewImage(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById("photoPreview").src = e.target.result;
            document.getElementById("photoPreview").style.display = "block";
        };
        reader.readAsDataURL(file);
    }
}

// Function to save case details
async function saveCase() {
    try {
        // Step 1: Send text-based case data first
        const caseId = await sendCaseData();
        if (!caseId) {
            alert("Failed to save case details. Aborting image upload.");
            return;
        }

        // Step 2: Upload images separately and send file paths to Flask
        await uploadImages(caseId);

        alert("Case and images saved successfully!");
    } catch (error) {
        console.error("Error:", error);
        alert("An error occurred while saving the case.");
    }
}

// Function to send text-based case details
async function sendCaseData() {
    const caseData = {
        suspectName: document.getElementById("suspectName").value,
        fatherName: document.getElementById("fatherName").value,
        motherName: document.getElementById("motherName").value,
        suspectAge: document.getElementById("suspectAge").value,
        suspectGender: document.getElementById("suspectGender").value,
        suspectDOB: document.getElementById("suspectDOB").value,
        AadhaarNumber: document.getElementById("AadhaarNumber").value,
        PhoneNumber: document.getElementById("PhoneNumber").value,
        modusOperandi: document.getElementById("modusoperandi").value,
        caseTitle: document.getElementById("caseTitle").value,
        BailDetails: document.getElementById("BailDetails").value,
        Firnumber: document.getElementById("Firnumber").value,
        caseDetails: document.getElementById("caseDetails").value,
        familyTies: document.getElementById("family_ties").value,
        evidenceCollected: document.getElementById("evidence_collected").value,
        crimeType: document.getElementById("crimeType").value,
        wantedLevel: document.getElementById("wantedlevel").value,
        officerName: document.getElementById("officerName").value,
        caseStatus: document.getElementById("caseStatus").value
    };

    try {
        const response = await fetch("/add_case", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(caseData)
        });

        const result = await response.json();
        if (!response.ok) {
            console.error("Failed to save case:", result.error);
            return null;
        }

        return result.case_id; // Return case ID to use for image upload
    } catch (error) {
        console.error("Error saving case:", error);
        return null;
    }
}

// Function to upload images and send file paths to Flask
async function uploadImages(caseId) {
    const imageInputs = [
        { id: "suspectPhoto", type: "suspectPhoto" },
        { id: "evidencePhoto", type: "evidencePhoto" },
        { id: "crimescenePhoto", type: "crimeScenePhoto" }
    ];

    for (let { id, type } of imageInputs) {
        let fileInput = document.getElementById(id);
        if (fileInput && fileInput.files.length > 0) {
            let formData = new FormData();
            formData.append("id", caseId);
            formData.append("image", fileInput.files[0]);
            formData.append("image_type", type);  // ✅ Send correct type

            try {
                let response = await fetch("/upload_case_images", {
                    method: "POST",
                    body: formData
                });

                let result = await response.json();
                if (!response.ok) {
                    console.error(`Error uploading ${id}:`, result.error);
                    alert(`Error uploading ${id}: ${result.error}`);
                    return;
                }

                console.log(`${id} uploaded successfully.`);
            } catch (error) {
                console.error(`Error uploading ${id}:`, error);
                alert(`An error occurred while uploading ${id}`);
            }
        }
    }
}

// 🔄 Save Search History in Local Storage
function saveSearchHistory(searchQuery) {
    let searches = JSON.parse(localStorage.getItem("recentSearches")) || [];
    
    // Remove duplicates
    searches = searches.filter(item => item !== searchQuery);

    // Add new search to the top
    searches.unshift(searchQuery);

    // Store max 5 searches
    if (searches.length > 5) {
        searches.pop();
    }

    localStorage.setItem("recentSearches", JSON.stringify(searches));

    // Update UI
    showRecentSearches();
}

// 📜 Show Recent Searches
function showRecentSearches() {
    let searches = JSON.parse(localStorage.getItem("recentSearches")) || [];
    let recentSearchesDiv = document.getElementById("recentSearches");
    let recentSearchList = document.getElementById("recentSearchList");

    // Clear old history
    recentSearchList.innerHTML = "";

    if (searches.length === 0) {
        recentSearchesDiv.style.display = "none";
        return;
    }

    // Add each search to the list
    searches.forEach(search => {
        let li = document.createElement("li");
        li.innerText = search;
        li.onclick = function () {
            document.getElementById("caseSearchInput").value = search;
            searchCases();
        };
        recentSearchList.appendChild(li);
    });

    // Show the dropdown
    recentSearchesDiv.style.display = "block";
}

// 📌 Hide Recent Searches When Clicking Outside
document.addEventListener("click", function (event) {
    let recentSearchesDiv = document.getElementById("recentSearches");
    if (event.target.id !== "caseSearchInput") {
        recentSearchesDiv.style.display = "none";
    }
});

// 📌 Hide Recent Searches When Clicking Outside
document.addEventListener("click", function (event) {
    let recentSearchesDiv = document.getElementById("recentSearches");
    if (event.target.id !== "caseSearchInput") {
        recentSearchesDiv.style.display = "none";
    }
});


// Function to search and filter cases
function searchCases() {
    let input = document.getElementById("caseSearchInput").value.toLowerCase();
    let caseList = document.getElementById("caseList");
    let caseItems = document.getElementsByClassName("case-item");

    console.log("User input: ", input); // Debugging log

    if (!caseList || caseItems.length === 0) {
        console.log("Error: No cases found!"); // Debugging line
        return;
    }

    let found = false;

    for (let i = 0; i < caseItems.length; i++) {
        let caseText = caseItems[i].textContent.toLowerCase();
        if (caseText.includes(input)) {
            caseItems[i].style.display = "block"; 
            found = true;
        } else {
            caseItems[i].style.display = "none";
        }
    }

    let noResults = document.getElementById("noResultsMessage");
    if (!noResults) {
        noResults = document.createElement("p");
        noResults.id = "noResultsMessage";
        noResults.style.color = "red";
        noResults.style.marginTop = "10px";
        caseList.appendChild(noResults);
    }

    noResults.textContent = found ? "" : "No matching cases found.";
}

function sendMessage() {
    let userInput = document.getElementById("userInput").value;
    if (!userInput.trim()) return;

    let chatbox = document.getElementById("chatbox");

    let userMessage = document.createElement("div");
    userMessage.classList.add("chat-message", "user");
    userMessage.innerText = userInput;
    chatbox.appendChild(userMessage);

    fetch(`/get_case?title=${encodeURIComponent(userInput)}`)
    .then(response => response.json())
    .then(data => {
        let botMessage = document.createElement("div");
        botMessage.classList.add("chat-message", "bot");

        if (data.message) {
            botMessage.innerText = "🔍 " + data.message;
        } else {
            botMessage.innerHTML = `<strong>Case Title:</strong> ${data.title} <br>
                                    <strong>Description:</strong> ${data.description} <br>
                                    <strong>Status:</strong> ${data.status}`;
        }

        chatbox.appendChild(botMessage);
        chatbox.scrollTop = chatbox.scrollHeight;
    })
    .catch(error => console.error("Error:", error));

    document.getElementById("userInput").value = "";
}


// Voice Recognition for Chat Input
document.getElementById("voiceInputButton").addEventListener("click", function() {
    let voiceBtn = document.getElementById("voiceInputButton");
    let recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = "en-US"; // Set language
    
    voiceBtn.classList.add("recording"); // Turn mic red & animate
    recognition.start(); // Start listening

    recognition.onresult = function(event) {
        let voiceText = event.results[0][0].transcript; // Get speech text
        document.getElementById("userInput").value = voiceText; // Insert into input box
    };

    recognition.onerror = function(event) {
        console.error("Voice recognition error:", event.error);
    };

    recognition.onend = function() {
        voiceBtn.classList.remove("recording"); // Reset mic color
    };
});

/* cases categories */

let caseCategories = [
    "Robbery in Downtown",
    "Fraud Investigation",
    "Missing Person Report",
    "Cybercrime Hacking",
    "Drug Trafficking Arrest",
    "Kidnapping Case",
    "Human Trafficking Incident",
    "Domestic Violence Report",
    "Terrorist Threat Investigation",
    "Money Laundering Case",
    "Vandalism and Property Damage",
    "Illegal Smuggling Case",
    "Arson Investigation",
    "Illegal Firearms Possession",
    "Bribery and Corruption"
];

console.log("Updated Case Categories:", caseCategories);

// Toggle the sidebar visibility when the button is clicked
function toggleSidebar() {
    var sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('open');
alert("Your browser does not support Speech Recognition.");
}
