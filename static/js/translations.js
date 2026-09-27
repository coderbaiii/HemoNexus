/**
 * HEMONEXAS Multi-Language Support System
 * Prepares the platform architecture for multi-language display.
 * Default: English (en). Extensible to Hindi (hi) and Bengali (bn).
 */
const TRANSLATIONS = {
  en: {
    brand: "HEMONEXAS",
    home: "Home",
    search: "Search Donors",
    donorDashboard: "Donor Dashboard",
    patientDashboard: "Patient Dashboard",
    adminConsole: "Admin Console",
    signIn: "Sign In",
    register: "Register",
    logOut: "Log Out",
    welcomeTitle: "Smart Blood Donor Management & Requirement-Based Matching",
    findDonorBtn: "Find Donors Now",
    medicalDisclaimer: "Medical Safety Disclaimer: Matching scores indicate operational search priority only. All donor screening and transfusion release are performed strictly by authorized blood bank medical staff.",
    noDonorsFound: "No suitable active donors found."
  },
  hi: {
    brand: "HEMONEXAS",
    home: "होम",
    search: "रक्तदाता खोजें",
    donorDashboard: "रक्तदाता डैशबोर्ड",
    patientDashboard: "मरीज डैशबोर्ड",
    adminConsole: "प्रशासन कंसोल",
    signIn: "साइन इन करें",
    register: "रजिस्टर करें",
    logOut: "लॉग आउट",
    welcomeTitle: "स्मार्ट रक्तदाता प्रबंधन एवं आवश्यकता-आधारित मिलान प्रणाली",
    findDonorBtn: "दाता खोजें",
    medicalDisclaimer: "चिकित्सा सुरक्षा अस्वीकरण: मिलान स्कोर केवल खोज प्राथमिकता दर्शाता है। अंतिम चिकित्सा परीक्षण अधिकृत ब्लड बैंक द्वारा किया जाता है।",
    noDonorsFound: "कोई उपयुक्त सक्रिय रक्तदाता नहीं मिला।"
  },
  bn: {
    brand: "HEMONEXAS",
    home: "হোম",
    search: "রক্তদাতা অনুসন্ধান",
    donorDashboard: "রক্তদাতা ড্যাশবোর্ড",
    patientDashboard: "রোগী ড্যাশবোর্ড",
    adminConsole: "অ্যাডমিন কনসোল",
    signIn: "সাইন ইন",
    register: "নিবন্ধন করুন",
    logOut: "লগ আউট",
    welcomeTitle: "স্মার্ট রক্তদাতা পরিচালনা ও চাহিদা-ভিত্তিক ম্যাচিং সিস্টেম",
    findDonorBtn: "রক্তদাতা খুঁজুন",
    medicalDisclaimer: "চিকিৎসা সুরক্ষা দাবিত্যাগ: ম্যাচিং স্কোর শুধুমাত্র অনুসন্ধান অগ্রাধিকার নির্দেশ করে। চূড়ান্ত চিকিৎসা পরীক্ষা অনুমোদিত ব্লাড সেন্টার দ্বারা সম্পন্ন হয়।",
    noDonorsFound: "কোনো উপযুক্ত সক্রিয় রক্তদাতা পাওয়া যায়নি।"
  }
};

function getSavedLanguage() {
  return localStorage.getItem("hemonexas_lang") || "en";
}

function setLanguage(lang) {
  if (!TRANSLATIONS[lang]) lang = "en";
  localStorage.setItem("hemonexas_lang", lang);
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) {
      el.textContent = TRANSLATIONS[lang][key];
    }
  });
  const selector = document.getElementById("langSelector");
  if (selector) selector.value = lang;
}

document.addEventListener("DOMContentLoaded", () => {
  const current = getSavedLanguage();
  setLanguage(current);
  const selector = document.getElementById("langSelector");
  if (selector) {
    selector.value = current;
    selector.addEventListener("change", (e) => {
      setLanguage(e.target.value);
    });
  }
});
