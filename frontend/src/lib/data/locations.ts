export interface CityLocation {
  name: string;
  pincodes: string[];
}

export interface StateLocation {
  name: string;
  cities: CityLocation[];
}

export interface CountryLocation {
  name: string;
  states: StateLocation[];
}

export const COUNTRIES_DATA: CountryLocation[] = [
  {
    "name": "India",
    "states": [
      {
        "name": "Andaman and Nicobar Islands",
        "cities": [
          {
            "name": "Car Nicobar",
            "pincodes": [
              "744301"
            ]
          },
          {
            "name": "Diglipur",
            "pincodes": [
              "744202"
            ]
          },
          {
            "name": "Mayabunder",
            "pincodes": [
              "744204"
            ]
          },
          {
            "name": "Port Blair",
            "pincodes": [
              "744101",
              "744102",
              "744103",
              "744105"
            ]
          },
          {
            "name": "Rangat",
            "pincodes": [
              "744205"
            ]
          }
        ]
      },
      {
        "name": "Andhra Pradesh",
        "cities": [
          {
            "name": "Anantapur",
            "pincodes": [
              "515001",
              "515002",
              "515004"
            ]
          },
          {
            "name": "Chittoor",
            "pincodes": [
              "517001",
              "517002"
            ]
          },
          {
            "name": "Eluru",
            "pincodes": [
              "534001",
              "534002",
              "534005"
            ]
          },
          {
            "name": "Guntur",
            "pincodes": [
              "522001",
              "522002",
              "522004",
              "522006"
            ]
          },
          {
            "name": "Kadapa",
            "pincodes": [
              "516001",
              "516002",
              "516004"
            ]
          },
          {
            "name": "Kakinada",
            "pincodes": [
              "533001",
              "533003",
              "533005"
            ]
          },
          {
            "name": "Kurnool",
            "pincodes": [
              "518001",
              "518002",
              "518003",
              "518004"
            ]
          },
          {
            "name": "Nellore",
            "pincodes": [
              "524001",
              "524002",
              "524003",
              "524004"
            ]
          },
          {
            "name": "Ongole",
            "pincodes": [
              "523001",
              "523002"
            ]
          },
          {
            "name": "Rajahmundry",
            "pincodes": [
              "533101",
              "533103",
              "533105"
            ]
          },
          {
            "name": "Srikakulam",
            "pincodes": [
              "532001",
              "532005"
            ]
          },
          {
            "name": "Tirupati",
            "pincodes": [
              "517501",
              "517502",
              "517507"
            ]
          },
          {
            "name": "Vijayawada",
            "pincodes": [
              "520001",
              "520002",
              "520008",
              "520010",
              "520012"
            ]
          },
          {
            "name": "Visakhapatnam",
            "pincodes": [
              "530001",
              "530002",
              "530016",
              "530017",
              "530020",
              "530045"
            ]
          },
          {
            "name": "Vizianagaram",
            "pincodes": [
              "535001",
              "535002"
            ]
          }
        ]
      },
      {
        "name": "Arunachal Pradesh",
        "cities": [
          {
            "name": "Bomdila",
            "pincodes": [
              "790001"
            ]
          },
          {
            "name": "Itanagar",
            "pincodes": [
              "791111",
              "791113"
            ]
          },
          {
            "name": "Naharlagun",
            "pincodes": [
              "791110"
            ]
          },
          {
            "name": "Pasighat",
            "pincodes": [
              "791102"
            ]
          },
          {
            "name": "Tawang",
            "pincodes": [
              "790104"
            ]
          },
          {
            "name": "Tezu",
            "pincodes": [
              "792001"
            ]
          },
          {
            "name": "Ziro",
            "pincodes": [
              "791120"
            ]
          }
        ]
      },
      {
        "name": "Assam",
        "cities": [
          {
            "name": "Bongaigaon",
            "pincodes": [
              "783380",
              "783381"
            ]
          },
          {
            "name": "Dibrugarh",
            "pincodes": [
              "786001",
              "786003",
              "786005"
            ]
          },
          {
            "name": "Guwahati",
            "pincodes": [
              "781001",
              "781005",
              "781006",
              "781012",
              "781022",
              "781035"
            ]
          },
          {
            "name": "Jorhat",
            "pincodes": [
              "785001",
              "785006",
              "785008"
            ]
          },
          {
            "name": "Nagaon",
            "pincodes": [
              "782001",
              "782002"
            ]
          },
          {
            "name": "Silchar",
            "pincodes": [
              "788001",
              "788002",
              "788005"
            ]
          },
          {
            "name": "Sivasagar",
            "pincodes": [
              "785640"
            ]
          },
          {
            "name": "Tezpur",
            "pincodes": [
              "784001",
              "784025"
            ]
          },
          {
            "name": "Tinsukia",
            "pincodes": [
              "786125",
              "786126"
            ]
          }
        ]
      },
      {
        "name": "Bihar",
        "cities": [
          {
            "name": "Arrah",
            "pincodes": [
              "802301",
              "802302"
            ]
          },
          {
            "name": "Begusarai",
            "pincodes": [
              "851101",
              "851117"
            ]
          },
          {
            "name": "Bhagalpur",
            "pincodes": [
              "812001",
              "812002",
              "812007"
            ]
          },
          {
            "name": "Bihar Sharif",
            "pincodes": [
              "803101",
              "803118"
            ]
          },
          {
            "name": "Chhapra",
            "pincodes": [
              "841301",
              "841302"
            ]
          },
          {
            "name": "Darbhanga",
            "pincodes": [
              "846001",
              "846004",
              "846005"
            ]
          },
          {
            "name": "Gaya",
            "pincodes": [
              "823001",
              "823002",
              "823003"
            ]
          },
          {
            "name": "Hajipur",
            "pincodes": [
              "844101",
              "844102"
            ]
          },
          {
            "name": "Katihar",
            "pincodes": [
              "854105",
              "854106"
            ]
          },
          {
            "name": "Munger",
            "pincodes": [
              "811201",
              "811202"
            ]
          },
          {
            "name": "Muzaffarpur",
            "pincodes": [
              "842001",
              "842002",
              "842003"
            ]
          },
          {
            "name": "Patna",
            "pincodes": [
              "800001",
              "800003",
              "800013",
              "800014",
              "800020",
              "800025"
            ]
          },
          {
            "name": "Purnia",
            "pincodes": [
              "854301",
              "854302"
            ]
          },
          {
            "name": "Saharsa",
            "pincodes": [
              "852201"
            ]
          },
          {
            "name": "Sasaram",
            "pincodes": [
              "821115"
            ]
          }
        ]
      },
      {
        "name": "Chandigarh",
        "cities": [
          {
            "name": "Chandigarh",
            "pincodes": [
              "160017",
              "160019",
              "160022",
              "160036",
              "160047"
            ]
          }
        ]
      },
      {
        "name": "Chhattisgarh",
        "cities": [
          {
            "name": "Ambikapur",
            "pincodes": [
              "497001"
            ]
          },
          {
            "name": "Bhilai",
            "pincodes": [
              "490001",
              "490006",
              "490020",
              "490023"
            ]
          },
          {
            "name": "Bilaspur",
            "pincodes": [
              "495001",
              "495004",
              "495006"
            ]
          },
          {
            "name": "Durg",
            "pincodes": [
              "491001",
              "491002"
            ]
          },
          {
            "name": "Jagdalpur",
            "pincodes": [
              "494001"
            ]
          },
          {
            "name": "Korba",
            "pincodes": [
              "495677",
              "495678"
            ]
          },
          {
            "name": "Raigarh",
            "pincodes": [
              "496001"
            ]
          },
          {
            "name": "Raipur",
            "pincodes": [
              "492001",
              "492002",
              "492006",
              "492010",
              "492015"
            ]
          },
          {
            "name": "Rajnandgaon",
            "pincodes": [
              "491441"
            ]
          }
        ]
      },
      {
        "name": "Dadra and Nagar Haveli and Daman and Diu",
        "cities": [
          {
            "name": "Daman",
            "pincodes": [
              "396210",
              "396220"
            ]
          },
          {
            "name": "Diu",
            "pincodes": [
              "362520"
            ]
          },
          {
            "name": "Silvassa",
            "pincodes": [
              "396230",
              "396235"
            ]
          }
        ]
      },
      {
        "name": "Delhi",
        "cities": [
          {
            "name": "Central Delhi",
            "pincodes": [
              "110002",
              "110005",
              "110055",
              "110060"
            ]
          },
          {
            "name": "Dwarka",
            "pincodes": [
              "110075",
              "110077",
              "110078"
            ]
          },
          {
            "name": "East Delhi",
            "pincodes": [
              "110031",
              "110051",
              "110091",
              "110092"
            ]
          },
          {
            "name": "New Delhi",
            "pincodes": [
              "110001",
              "110003",
              "110011",
              "110029",
              "110067"
            ]
          },
          {
            "name": "North Delhi",
            "pincodes": [
              "110006",
              "110007",
              "110009",
              "110054"
            ]
          },
          {
            "name": "North East Delhi",
            "pincodes": [
              "110053",
              "110093",
              "110094"
            ]
          },
          {
            "name": "North West Delhi",
            "pincodes": [
              "110034",
              "110052",
              "110085",
              "110088"
            ]
          },
          {
            "name": "Shahdara",
            "pincodes": [
              "110032",
              "110095"
            ]
          },
          {
            "name": "South Delhi",
            "pincodes": [
              "110016",
              "110017",
              "110019",
              "110048",
              "110049"
            ]
          },
          {
            "name": "South East Delhi",
            "pincodes": [
              "110014",
              "110020",
              "110025",
              "110044",
              "110065"
            ]
          },
          {
            "name": "South West Delhi",
            "pincodes": [
              "110010",
              "110021",
              "110037",
              "110070"
            ]
          },
          {
            "name": "West Delhi",
            "pincodes": [
              "110015",
              "110018",
              "110027",
              "110058"
            ]
          }
        ]
      },
      {
        "name": "Goa",
        "cities": [
          {
            "name": "Bicholim",
            "pincodes": [
              "403504"
            ]
          },
          {
            "name": "Mapusa",
            "pincodes": [
              "403507"
            ]
          },
          {
            "name": "Margao",
            "pincodes": [
              "403601",
              "403602"
            ]
          },
          {
            "name": "Panaji",
            "pincodes": [
              "403001",
              "403002"
            ]
          },
          {
            "name": "Ponda",
            "pincodes": [
              "403401"
            ]
          },
          {
            "name": "Vasco da Gama",
            "pincodes": [
              "403802"
            ]
          }
        ]
      },
      {
        "name": "Gujarat",
        "cities": [
          {
            "name": "Ahmedabad",
            "pincodes": [
              "380001",
              "380006",
              "380009",
              "380015",
              "380054",
              "380058"
            ]
          },
          {
            "name": "Anand",
            "pincodes": [
              "388001",
              "388120"
            ]
          },
          {
            "name": "Bharuch",
            "pincodes": [
              "392001",
              "392002"
            ]
          },
          {
            "name": "Bhavnagar",
            "pincodes": [
              "364001",
              "364002",
              "364004"
            ]
          },
          {
            "name": "Bhuj",
            "pincodes": [
              "370001"
            ]
          },
          {
            "name": "Gandhinagar",
            "pincodes": [
              "382010",
              "382016",
              "382024",
              "382028"
            ]
          },
          {
            "name": "Jamnagar",
            "pincodes": [
              "361001",
              "361005",
              "361008"
            ]
          },
          {
            "name": "Junagadh",
            "pincodes": [
              "362001",
              "362002"
            ]
          },
          {
            "name": "Mehsana",
            "pincodes": [
              "384001",
              "384002"
            ]
          },
          {
            "name": "Morbi",
            "pincodes": [
              "363641",
              "363642"
            ]
          },
          {
            "name": "Nadiad",
            "pincodes": [
              "387001",
              "387002"
            ]
          },
          {
            "name": "Navsari",
            "pincodes": [
              "396445"
            ]
          },
          {
            "name": "Porbandar",
            "pincodes": [
              "360575"
            ]
          },
          {
            "name": "Rajkot",
            "pincodes": [
              "360001",
              "360002",
              "360004",
              "360005"
            ]
          },
          {
            "name": "Surat",
            "pincodes": [
              "395001",
              "395002",
              "395003",
              "395007",
              "395009"
            ]
          },
          {
            "name": "Vadodara",
            "pincodes": [
              "390001",
              "390007",
              "390011",
              "390020"
            ]
          },
          {
            "name": "Valsad",
            "pincodes": [
              "396001"
            ]
          },
          {
            "name": "Vapi",
            "pincodes": [
              "396191",
              "396195"
            ]
          }
        ]
      },
      {
        "name": "Haryana",
        "cities": [
          {
            "name": "Ambala",
            "pincodes": [
              "133001",
              "134003"
            ]
          },
          {
            "name": "Bahadurgarh",
            "pincodes": [
              "124507"
            ]
          },
          {
            "name": "Bhiwani",
            "pincodes": [
              "127021"
            ]
          },
          {
            "name": "Faridabad",
            "pincodes": [
              "121001",
              "121002",
              "121003",
              "121007",
              "121008"
            ]
          },
          {
            "name": "Gurugram",
            "pincodes": [
              "122001",
              "122002",
              "122003",
              "122018",
              "122022",
              "122050"
            ]
          },
          {
            "name": "Hisar",
            "pincodes": [
              "125001",
              "125005"
            ]
          },
          {
            "name": "Karnal",
            "pincodes": [
              "132001"
            ]
          },
          {
            "name": "Palwal",
            "pincodes": [
              "121102"
            ]
          },
          {
            "name": "Panchkula",
            "pincodes": [
              "134109",
              "134112",
              "134114"
            ]
          },
          {
            "name": "Panipat",
            "pincodes": [
              "132103",
              "132104"
            ]
          },
          {
            "name": "Rewari",
            "pincodes": [
              "123401"
            ]
          },
          {
            "name": "Rohtak",
            "pincodes": [
              "124001"
            ]
          },
          {
            "name": "Sirsa",
            "pincodes": [
              "125055"
            ]
          },
          {
            "name": "Sonipat",
            "pincodes": [
              "131001"
            ]
          },
          {
            "name": "Yamunanagar",
            "pincodes": [
              "135001"
            ]
          }
        ]
      },
      {
        "name": "Himachal Pradesh",
        "cities": [
          {
            "name": "Baddi",
            "pincodes": [
              "173205"
            ]
          },
          {
            "name": "Bilaspur",
            "pincodes": [
              "174001"
            ]
          },
          {
            "name": "Dharamshala",
            "pincodes": [
              "176215",
              "176219"
            ]
          },
          {
            "name": "Hamirpur",
            "pincodes": [
              "177001"
            ]
          },
          {
            "name": "Kullu",
            "pincodes": [
              "175101"
            ]
          },
          {
            "name": "Manali",
            "pincodes": [
              "175131"
            ]
          },
          {
            "name": "Mandi",
            "pincodes": [
              "175001"
            ]
          },
          {
            "name": "Shimla",
            "pincodes": [
              "171001",
              "171002",
              "171003",
              "171009"
            ]
          },
          {
            "name": "Solan",
            "pincodes": [
              "173211",
              "173212"
            ]
          },
          {
            "name": "Una",
            "pincodes": [
              "174303"
            ]
          }
        ]
      },
      {
        "name": "Jammu and Kashmir",
        "cities": [
          {
            "name": "Anantnag",
            "pincodes": [
              "192101"
            ]
          },
          {
            "name": "Baramulla",
            "pincodes": [
              "193101"
            ]
          },
          {
            "name": "Jammu",
            "pincodes": [
              "180001",
              "180003",
              "180004",
              "180012"
            ]
          },
          {
            "name": "Kathua",
            "pincodes": [
              "184101"
            ]
          },
          {
            "name": "Pulwama",
            "pincodes": [
              "192301"
            ]
          },
          {
            "name": "Rajouri",
            "pincodes": [
              "185131"
            ]
          },
          {
            "name": "Sopore",
            "pincodes": [
              "193201"
            ]
          },
          {
            "name": "Srinagar",
            "pincodes": [
              "190001",
              "190002",
              "190008",
              "190010"
            ]
          },
          {
            "name": "Udhampur",
            "pincodes": [
              "182101"
            ]
          }
        ]
      },
      {
        "name": "Jharkhand",
        "cities": [
          {
            "name": "Bokaro Steel City",
            "pincodes": [
              "827001",
              "827004",
              "827006"
            ]
          },
          {
            "name": "Deoghar",
            "pincodes": [
              "814112"
            ]
          },
          {
            "name": "Dhanbad",
            "pincodes": [
              "826001",
              "826004"
            ]
          },
          {
            "name": "Giridih",
            "pincodes": [
              "815301"
            ]
          },
          {
            "name": "Hazaribagh",
            "pincodes": [
              "825301"
            ]
          },
          {
            "name": "Jamshedpur",
            "pincodes": [
              "831001",
              "831003",
              "831004",
              "831011"
            ]
          },
          {
            "name": "Medininagar",
            "pincodes": [
              "822101"
            ]
          },
          {
            "name": "Ramgarh",
            "pincodes": [
              "829122"
            ]
          },
          {
            "name": "Ranchi",
            "pincodes": [
              "834001",
              "834002",
              "834004",
              "834008",
              "834010"
            ]
          }
        ]
      },
      {
        "name": "Karnataka",
        "cities": [
          {
            "name": "Ballari",
            "pincodes": [
              "583101",
              "583103"
            ]
          },
          {
            "name": "Belagavi",
            "pincodes": [
              "590001",
              "590002",
              "590016"
            ]
          },
          {
            "name": "Bengaluru",
            "pincodes": [
              "560001",
              "560002",
              "560025",
              "560034",
              "560037",
              "560066",
              "560100",
              "560103"
            ]
          },
          {
            "name": "Bidar",
            "pincodes": [
              "585401"
            ]
          },
          {
            "name": "Chikkamagaluru",
            "pincodes": [
              "577101"
            ]
          },
          {
            "name": "Davanagere",
            "pincodes": [
              "577001",
              "577002"
            ]
          },
          {
            "name": "Hassan",
            "pincodes": [
              "573201"
            ]
          },
          {
            "name": "Hosapete",
            "pincodes": [
              "583201"
            ]
          },
          {
            "name": "Hubballi-Dharwad",
            "pincodes": [
              "580020",
              "580029",
              "580031"
            ]
          },
          {
            "name": "Kalaburagi",
            "pincodes": [
              "585101",
              "585102",
              "585103"
            ]
          },
          {
            "name": "Kolar",
            "pincodes": [
              "563101"
            ]
          },
          {
            "name": "Mandya",
            "pincodes": [
              "571401"
            ]
          },
          {
            "name": "Mangaluru",
            "pincodes": [
              "575001",
              "575002",
              "575003",
              "575006"
            ]
          },
          {
            "name": "Mysuru",
            "pincodes": [
              "570001",
              "570004",
              "570012",
              "570020"
            ]
          },
          {
            "name": "Raichur",
            "pincodes": [
              "584101"
            ]
          },
          {
            "name": "Shivamogga",
            "pincodes": [
              "577201",
              "577204"
            ]
          },
          {
            "name": "Tumakuru",
            "pincodes": [
              "572101",
              "572102"
            ]
          },
          {
            "name": "Udupi",
            "pincodes": [
              "576101",
              "576102"
            ]
          },
          {
            "name": "Vijayapura",
            "pincodes": [
              "586101",
              "586103"
            ]
          }
        ]
      },
      {
        "name": "Kerala",
        "cities": [
          {
            "name": "Alappuzha",
            "pincodes": [
              "688001",
              "688011"
            ]
          },
          {
            "name": "Kanhangad",
            "pincodes": [
              "671315"
            ]
          },
          {
            "name": "Kannur",
            "pincodes": [
              "670001",
              "670002"
            ]
          },
          {
            "name": "Kochi",
            "pincodes": [
              "682001",
              "682011",
              "682016",
              "682024",
              "682030",
              "682036"
            ]
          },
          {
            "name": "Kollam",
            "pincodes": [
              "691001",
              "691008"
            ]
          },
          {
            "name": "Kottayam",
            "pincodes": [
              "686001",
              "686002"
            ]
          },
          {
            "name": "Kozhikode",
            "pincodes": [
              "673001",
              "673004",
              "673016",
              "673020"
            ]
          },
          {
            "name": "Malappuram",
            "pincodes": [
              "676505"
            ]
          },
          {
            "name": "Palakkad",
            "pincodes": [
              "678001",
              "678014"
            ]
          },
          {
            "name": "Thalassery",
            "pincodes": [
              "670101"
            ]
          },
          {
            "name": "Thiruvananthapuram",
            "pincodes": [
              "695001",
              "695004",
              "695011",
              "695014",
              "695033"
            ]
          },
          {
            "name": "Thrissur",
            "pincodes": [
              "680001",
              "680004",
              "680020"
            ]
          }
        ]
      },
      {
        "name": "Ladakh",
        "cities": [
          {
            "name": "Kargil",
            "pincodes": [
              "194103",
              "194105"
            ]
          },
          {
            "name": "Leh",
            "pincodes": [
              "194101",
              "194104"
            ]
          }
        ]
      },
      {
        "name": "Lakshadweep",
        "cities": [
          {
            "name": "Agatti",
            "pincodes": [
              "682553"
            ]
          },
          {
            "name": "Amini",
            "pincodes": [
              "682552"
            ]
          },
          {
            "name": "Andrott",
            "pincodes": [
              "682551"
            ]
          },
          {
            "name": "Kavaratti",
            "pincodes": [
              "682555"
            ]
          },
          {
            "name": "Minicoy",
            "pincodes": [
              "682559"
            ]
          }
        ]
      },
      {
        "name": "Madhya Pradesh",
        "cities": [
          {
            "name": "Bhopal",
            "pincodes": [
              "462001",
              "462003",
              "462011",
              "462016",
              "462023"
            ]
          },
          {
            "name": "Burhanpur",
            "pincodes": [
              "450331"
            ]
          },
          {
            "name": "Chhindwara",
            "pincodes": [
              "480001"
            ]
          },
          {
            "name": "Dewas",
            "pincodes": [
              "455001"
            ]
          },
          {
            "name": "Gwalior",
            "pincodes": [
              "474001",
              "474002",
              "474006",
              "474011"
            ]
          },
          {
            "name": "Indore",
            "pincodes": [
              "452001",
              "452002",
              "452007",
              "452010",
              "452016",
              "452020"
            ]
          },
          {
            "name": "Jabalpur",
            "pincodes": [
              "482001",
              "482002",
              "482004"
            ]
          },
          {
            "name": "Katni",
            "pincodes": [
              "483501"
            ]
          },
          {
            "name": "Khandwa",
            "pincodes": [
              "450001"
            ]
          },
          {
            "name": "Ratlam",
            "pincodes": [
              "457001"
            ]
          },
          {
            "name": "Rewa",
            "pincodes": [
              "486001"
            ]
          },
          {
            "name": "Sagar",
            "pincodes": [
              "470001",
              "470002"
            ]
          },
          {
            "name": "Satna",
            "pincodes": [
              "485001"
            ]
          },
          {
            "name": "Singrauli",
            "pincodes": [
              "486889"
            ]
          },
          {
            "name": "Ujjain",
            "pincodes": [
              "456001",
              "456006",
              "456010"
            ]
          }
        ]
      },
      {
        "name": "Maharashtra",
        "cities": [
          {
            "name": "Ahmednagar",
            "pincodes": [
              "414001",
              "414003"
            ]
          },
          {
            "name": "Akola",
            "pincodes": [
              "444001",
              "444002"
            ]
          },
          {
            "name": "Amravati",
            "pincodes": [
              "444601",
              "444602"
            ]
          },
          {
            "name": "Chandrapur",
            "pincodes": [
              "442401",
              "442402"
            ]
          },
          {
            "name": "Chhatrapati Sambhajinagar",
            "pincodes": [
              "431001",
              "431003",
              "431005"
            ]
          },
          {
            "name": "Dhule",
            "pincodes": [
              "424001",
              "424002"
            ]
          },
          {
            "name": "Jalgaon",
            "pincodes": [
              "425001",
              "425002"
            ]
          },
          {
            "name": "Jalna",
            "pincodes": [
              "431203"
            ]
          },
          {
            "name": "Kalyan-Dombivli",
            "pincodes": [
              "421201",
              "421202",
              "421301"
            ]
          },
          {
            "name": "Kolhapur",
            "pincodes": [
              "416001",
              "416003",
              "416008"
            ]
          },
          {
            "name": "Latur",
            "pincodes": [
              "413512",
              "413531"
            ]
          },
          {
            "name": "Mumbai",
            "pincodes": [
              "400001",
              "400018",
              "400028",
              "400051",
              "400076",
              "400093",
              "400099"
            ]
          },
          {
            "name": "Nagpur",
            "pincodes": [
              "440001",
              "440010",
              "440012",
              "440022",
              "440025"
            ]
          },
          {
            "name": "Nanded",
            "pincodes": [
              "431601",
              "431602"
            ]
          },
          {
            "name": "Nashik",
            "pincodes": [
              "422001",
              "422003",
              "422007",
              "422009",
              "422013"
            ]
          },
          {
            "name": "Navi Mumbai",
            "pincodes": [
              "400703",
              "400705",
              "400706",
              "400709",
              "400710"
            ]
          },
          {
            "name": "Panvel",
            "pincodes": [
              "410206",
              "410218"
            ]
          },
          {
            "name": "Parbhani",
            "pincodes": [
              "431401"
            ]
          },
          {
            "name": "Pimpri-Chinchwad",
            "pincodes": [
              "411017",
              "411018",
              "411019",
              "411033"
            ]
          },
          {
            "name": "Pune",
            "pincodes": [
              "411001",
              "411004",
              "411014",
              "411028",
              "411045",
              "411057"
            ]
          },
          {
            "name": "Ratnagiri",
            "pincodes": [
              "415612"
            ]
          },
          {
            "name": "Sangli",
            "pincodes": [
              "416416"
            ]
          },
          {
            "name": "Satara",
            "pincodes": [
              "415001",
              "415002"
            ]
          },
          {
            "name": "Solapur",
            "pincodes": [
              "413001",
              "413002",
              "413006"
            ]
          },
          {
            "name": "Thane",
            "pincodes": [
              "400601",
              "400602",
              "400604",
              "400607",
              "400615"
            ]
          },
          {
            "name": "Vasai-Virar",
            "pincodes": [
              "401201",
              "401202",
              "401303"
            ]
          }
        ]
      },
      {
        "name": "Manipur",
        "cities": [
          {
            "name": "Bishnupur",
            "pincodes": [
              "795126"
            ]
          },
          {
            "name": "Churachandpur",
            "pincodes": [
              "795128"
            ]
          },
          {
            "name": "Imphal",
            "pincodes": [
              "795001",
              "795002",
              "795004"
            ]
          },
          {
            "name": "Kakching",
            "pincodes": [
              "795103"
            ]
          },
          {
            "name": "Thoubal",
            "pincodes": [
              "795138"
            ]
          },
          {
            "name": "Ukhrul",
            "pincodes": [
              "795142"
            ]
          }
        ]
      },
      {
        "name": "Meghalaya",
        "cities": [
          {
            "name": "Jowai",
            "pincodes": [
              "793150"
            ]
          },
          {
            "name": "Nongpoh",
            "pincodes": [
              "793102"
            ]
          },
          {
            "name": "Shillong",
            "pincodes": [
              "793001",
              "793003",
              "793008",
              "793014"
            ]
          },
          {
            "name": "Tura",
            "pincodes": [
              "794001",
              "794002"
            ]
          },
          {
            "name": "Williamnagar",
            "pincodes": [
              "794111"
            ]
          }
        ]
      },
      {
        "name": "Mizoram",
        "cities": [
          {
            "name": "Aizawl",
            "pincodes": [
              "796001",
              "796005",
              "796009",
              "796012"
            ]
          },
          {
            "name": "Champhai",
            "pincodes": [
              "796321"
            ]
          },
          {
            "name": "Kolasib",
            "pincodes": [
              "796081"
            ]
          },
          {
            "name": "Lunglei",
            "pincodes": [
              "796701"
            ]
          },
          {
            "name": "Saiha",
            "pincodes": [
              "796901"
            ]
          },
          {
            "name": "Serchhip",
            "pincodes": [
              "796181"
            ]
          }
        ]
      },
      {
        "name": "Nagaland",
        "cities": [
          {
            "name": "Dimapur",
            "pincodes": [
              "797112",
              "797113",
              "797115"
            ]
          },
          {
            "name": "Kohima",
            "pincodes": [
              "797001",
              "797002",
              "797004"
            ]
          },
          {
            "name": "Mokokchung",
            "pincodes": [
              "798601"
            ]
          },
          {
            "name": "Tuensang",
            "pincodes": [
              "798612"
            ]
          },
          {
            "name": "Wokha",
            "pincodes": [
              "797111"
            ]
          },
          {
            "name": "Zunheboto",
            "pincodes": [
              "798620"
            ]
          }
        ]
      },
      {
        "name": "Odisha",
        "cities": [
          {
            "name": "Balasore",
            "pincodes": [
              "756001",
              "756003"
            ]
          },
          {
            "name": "Baripada",
            "pincodes": [
              "757001"
            ]
          },
          {
            "name": "Berhampur",
            "pincodes": [
              "760001",
              "760002",
              "760004"
            ]
          },
          {
            "name": "Bhadrak",
            "pincodes": [
              "756100"
            ]
          },
          {
            "name": "Bhubaneswar",
            "pincodes": [
              "751001",
              "751002",
              "751007",
              "751010",
              "751024",
              "751030"
            ]
          },
          {
            "name": "Cuttack",
            "pincodes": [
              "753001",
              "753002",
              "753003",
              "753008"
            ]
          },
          {
            "name": "Jeypore",
            "pincodes": [
              "764001"
            ]
          },
          {
            "name": "Jharsuguda",
            "pincodes": [
              "768201"
            ]
          },
          {
            "name": "Puri",
            "pincodes": [
              "752001",
              "752002"
            ]
          },
          {
            "name": "Rourkela",
            "pincodes": [
              "769001",
              "769004",
              "769012"
            ]
          },
          {
            "name": "Sambalpur",
            "pincodes": [
              "768001",
              "768004"
            ]
          }
        ]
      },
      {
        "name": "Puducherry",
        "cities": [
          {
            "name": "Karaikal",
            "pincodes": [
              "609602"
            ]
          },
          {
            "name": "Mahe",
            "pincodes": [
              "673310"
            ]
          },
          {
            "name": "Puducherry",
            "pincodes": [
              "605001",
              "605004",
              "605008",
              "605011"
            ]
          },
          {
            "name": "Yanam",
            "pincodes": [
              "533464"
            ]
          }
        ]
      },
      {
        "name": "Punjab",
        "cities": [
          {
            "name": "Abohar",
            "pincodes": [
              "152116"
            ]
          },
          {
            "name": "Amritsar",
            "pincodes": [
              "143001",
              "143002",
              "143005",
              "143006"
            ]
          },
          {
            "name": "Bathinda",
            "pincodes": [
              "151001",
              "151005"
            ]
          },
          {
            "name": "Firozpur",
            "pincodes": [
              "152002"
            ]
          },
          {
            "name": "Hoshiarpur",
            "pincodes": [
              "146001"
            ]
          },
          {
            "name": "Jalandhar",
            "pincodes": [
              "144001",
              "144002",
              "144004",
              "144008"
            ]
          },
          {
            "name": "Ludhiana",
            "pincodes": [
              "141001",
              "141002",
              "141003",
              "141008",
              "141010"
            ]
          },
          {
            "name": "Moga",
            "pincodes": [
              "142001"
            ]
          },
          {
            "name": "Mohali",
            "pincodes": [
              "160055",
              "160059",
              "160062",
              "160071"
            ]
          },
          {
            "name": "Pathankot",
            "pincodes": [
              "145001"
            ]
          },
          {
            "name": "Patiala",
            "pincodes": [
              "147001",
              "147002",
              "147004"
            ]
          },
          {
            "name": "Phagwara",
            "pincodes": [
              "144401"
            ]
          }
        ]
      },
      {
        "name": "Rajasthan",
        "cities": [
          {
            "name": "Ajmer",
            "pincodes": [
              "305001",
              "305004"
            ]
          },
          {
            "name": "Alwar",
            "pincodes": [
              "301001"
            ]
          },
          {
            "name": "Bharatpur",
            "pincodes": [
              "321001"
            ]
          },
          {
            "name": "Bhilwara",
            "pincodes": [
              "311001"
            ]
          },
          {
            "name": "Bikaner",
            "pincodes": [
              "334001",
              "334003"
            ]
          },
          {
            "name": "Chittorgarh",
            "pincodes": [
              "312001"
            ]
          },
          {
            "name": "Jaipur",
            "pincodes": [
              "302001",
              "302004",
              "302015",
              "302017",
              "302020",
              "302033"
            ]
          },
          {
            "name": "Jodhpur",
            "pincodes": [
              "342001",
              "342003",
              "342005",
              "342008"
            ]
          },
          {
            "name": "Kota",
            "pincodes": [
              "324001",
              "324005",
              "324007"
            ]
          },
          {
            "name": "Pali",
            "pincodes": [
              "306401"
            ]
          },
          {
            "name": "Sikar",
            "pincodes": [
              "332001"
            ]
          },
          {
            "name": "Sri Ganganagar",
            "pincodes": [
              "335001"
            ]
          },
          {
            "name": "Udaipur",
            "pincodes": [
              "313001",
              "313002",
              "313004"
            ]
          }
        ]
      },
      {
        "name": "Sikkim",
        "cities": [
          {
            "name": "Gangtok",
            "pincodes": [
              "737101",
              "737102",
              "737103"
            ]
          },
          {
            "name": "Geyzing",
            "pincodes": [
              "737111"
            ]
          },
          {
            "name": "Mangan",
            "pincodes": [
              "737116"
            ]
          },
          {
            "name": "Namchi",
            "pincodes": [
              "737126"
            ]
          },
          {
            "name": "Rangpo",
            "pincodes": [
              "737132"
            ]
          }
        ]
      },
      {
        "name": "Tamil Nadu",
        "cities": [
          {
            "name": "Chennai",
            "pincodes": [
              "600001",
              "600002",
              "600017",
              "600028",
              "600034",
              "600096",
              "600113"
            ]
          },
          {
            "name": "Coimbatore",
            "pincodes": [
              "641001",
              "641004",
              "641014",
              "641018",
              "641062"
            ]
          },
          {
            "name": "Cuddalore",
            "pincodes": [
              "607001"
            ]
          },
          {
            "name": "Dindigul",
            "pincodes": [
              "624001"
            ]
          },
          {
            "name": "Erode",
            "pincodes": [
              "638001",
              "638002",
              "638011"
            ]
          },
          {
            "name": "Hosur",
            "pincodes": [
              "635109",
              "635126"
            ]
          },
          {
            "name": "Kancheepuram",
            "pincodes": [
              "631501"
            ]
          },
          {
            "name": "Kumbakonam",
            "pincodes": [
              "612001"
            ]
          },
          {
            "name": "Madurai",
            "pincodes": [
              "625001",
              "625002",
              "625009",
              "625020"
            ]
          },
          {
            "name": "Nagercoil",
            "pincodes": [
              "629001"
            ]
          },
          {
            "name": "Ranipet",
            "pincodes": [
              "632401"
            ]
          },
          {
            "name": "Salem",
            "pincodes": [
              "636001",
              "636004",
              "636007"
            ]
          },
          {
            "name": "Thanjavur",
            "pincodes": [
              "613001"
            ]
          },
          {
            "name": "Thoothukudi",
            "pincodes": [
              "628001",
              "628002"
            ]
          },
          {
            "name": "Tiruchirappalli",
            "pincodes": [
              "620001",
              "620002",
              "620015",
              "620018"
            ]
          },
          {
            "name": "Tirunelveli",
            "pincodes": [
              "627001",
              "627002"
            ]
          },
          {
            "name": "Tiruppur",
            "pincodes": [
              "641601",
              "641602",
              "641604"
            ]
          },
          {
            "name": "Udhagamandalam (Ooty)",
            "pincodes": [
              "643001"
            ]
          },
          {
            "name": "Vellore",
            "pincodes": [
              "632001",
              "632004"
            ]
          }
        ]
      },
      {
        "name": "Telangana",
        "cities": [
          {
            "name": "Adilabad",
            "pincodes": [
              "504001"
            ]
          },
          {
            "name": "Hyderabad",
            "pincodes": [
              "500001",
              "500003",
              "500032",
              "500034",
              "500081",
              "500082",
              "500084"
            ]
          },
          {
            "name": "Jagtial",
            "pincodes": [
              "505327"
            ]
          },
          {
            "name": "Karimnagar",
            "pincodes": [
              "505001",
              "505002"
            ]
          },
          {
            "name": "Khammam",
            "pincodes": [
              "507001",
              "507002",
              "507003"
            ]
          },
          {
            "name": "Mahbubnagar",
            "pincodes": [
              "509001",
              "509002"
            ]
          },
          {
            "name": "Mancherial",
            "pincodes": [
              "504208"
            ]
          },
          {
            "name": "Miryalaguda",
            "pincodes": [
              "508207"
            ]
          },
          {
            "name": "Nalgonda",
            "pincodes": [
              "508001"
            ]
          },
          {
            "name": "Nizamabad",
            "pincodes": [
              "503001",
              "503002",
              "503003"
            ]
          },
          {
            "name": "Ramagundam",
            "pincodes": [
              "505208",
              "505209"
            ]
          },
          {
            "name": "Siddipet",
            "pincodes": [
              "502103"
            ]
          },
          {
            "name": "Suryapet",
            "pincodes": [
              "508213"
            ]
          },
          {
            "name": "Warangal",
            "pincodes": [
              "506001",
              "506002",
              "506004",
              "506009"
            ]
          }
        ]
      },
      {
        "name": "Tripura",
        "cities": [
          {
            "name": "Agartala",
            "pincodes": [
              "799001",
              "799002",
              "799005",
              "799006"
            ]
          },
          {
            "name": "Belonia",
            "pincodes": [
              "799155"
            ]
          },
          {
            "name": "Dharmanagar",
            "pincodes": [
              "799250"
            ]
          },
          {
            "name": "Kailashahar",
            "pincodes": [
              "799277"
            ]
          },
          {
            "name": "Khowai",
            "pincodes": [
              "799201"
            ]
          },
          {
            "name": "Udaipur",
            "pincodes": [
              "799120"
            ]
          }
        ]
      },
      {
        "name": "Uttar Pradesh",
        "cities": [
          {
            "name": "Agra",
            "pincodes": [
              "282001",
              "282002",
              "282004",
              "282007"
            ]
          },
          {
            "name": "Aligarh",
            "pincodes": [
              "202001",
              "202002"
            ]
          },
          {
            "name": "Ayodhya",
            "pincodes": [
              "224123",
              "224001"
            ]
          },
          {
            "name": "Bareilly",
            "pincodes": [
              "243001",
              "243003",
              "243005"
            ]
          },
          {
            "name": "Firozabad",
            "pincodes": [
              "283203"
            ]
          },
          {
            "name": "Ghaziabad",
            "pincodes": [
              "201001",
              "201002",
              "201010",
              "201012"
            ]
          },
          {
            "name": "Gorakhpur",
            "pincodes": [
              "273001",
              "273005"
            ]
          },
          {
            "name": "Greater Noida",
            "pincodes": [
              "201306",
              "201308",
              "201310"
            ]
          },
          {
            "name": "Jhansi",
            "pincodes": [
              "284001",
              "284002"
            ]
          },
          {
            "name": "Kanpur",
            "pincodes": [
              "208001",
              "208002",
              "208012",
              "208024"
            ]
          },
          {
            "name": "Lucknow",
            "pincodes": [
              "226001",
              "226003",
              "226010",
              "226016",
              "226024",
              "226028"
            ]
          },
          {
            "name": "Mathura",
            "pincodes": [
              "281001",
              "281003"
            ]
          },
          {
            "name": "Meerut",
            "pincodes": [
              "250001",
              "250002",
              "250004"
            ]
          },
          {
            "name": "Moradabad",
            "pincodes": [
              "244001"
            ]
          },
          {
            "name": "Muzaffarnagar",
            "pincodes": [
              "251001"
            ]
          },
          {
            "name": "Noida",
            "pincodes": [
              "201301",
              "201303",
              "201304",
              "201307",
              "201313"
            ]
          },
          {
            "name": "Prayagraj",
            "pincodes": [
              "211001",
              "211002",
              "211003",
              "211006"
            ]
          },
          {
            "name": "Saharanpur",
            "pincodes": [
              "247001"
            ]
          },
          {
            "name": "Varanasi",
            "pincodes": [
              "221001",
              "221002",
              "221005",
              "221010"
            ]
          }
        ]
      },
      {
        "name": "Uttarakhand",
        "cities": [
          {
            "name": "Dehradun",
            "pincodes": [
              "248001",
              "248002",
              "248006",
              "248007",
              "248008"
            ]
          },
          {
            "name": "Haldwani",
            "pincodes": [
              "263139"
            ]
          },
          {
            "name": "Haridwar",
            "pincodes": [
              "249401",
              "249403",
              "249407"
            ]
          },
          {
            "name": "Kashipur",
            "pincodes": [
              "244713"
            ]
          },
          {
            "name": "Mussoorie",
            "pincodes": [
              "248179"
            ]
          },
          {
            "name": "Nainital",
            "pincodes": [
              "263001",
              "263002"
            ]
          },
          {
            "name": "Rishikesh",
            "pincodes": [
              "249201"
            ]
          },
          {
            "name": "Roorkee",
            "pincodes": [
              "247667"
            ]
          },
          {
            "name": "Rudrapur",
            "pincodes": [
              "263153"
            ]
          }
        ]
      },
      {
        "name": "West Bengal",
        "cities": [
          {
            "name": "Asansol",
            "pincodes": [
              "713301",
              "713303",
              "713304"
            ]
          },
          {
            "name": "Baharampur",
            "pincodes": [
              "742101"
            ]
          },
          {
            "name": "Bardhaman",
            "pincodes": [
              "713101",
              "713102"
            ]
          },
          {
            "name": "Darjeeling",
            "pincodes": [
              "734101"
            ]
          },
          {
            "name": "Durgapur",
            "pincodes": [
              "713201",
              "713206",
              "713216",
              "713218"
            ]
          },
          {
            "name": "Haldia",
            "pincodes": [
              "721602",
              "721605"
            ]
          },
          {
            "name": "Howrah",
            "pincodes": [
              "711101",
              "711102",
              "711104",
              "711106"
            ]
          },
          {
            "name": "Jalpaiguri",
            "pincodes": [
              "735101"
            ]
          },
          {
            "name": "Kharagpur",
            "pincodes": [
              "721301",
              "721302"
            ]
          },
          {
            "name": "Kolkata",
            "pincodes": [
              "700001",
              "700016",
              "700020",
              "700029",
              "700091",
              "700156"
            ]
          },
          {
            "name": "Malda",
            "pincodes": [
              "732101"
            ]
          },
          {
            "name": "Siliguri",
            "pincodes": [
              "734001",
              "734003",
              "734005"
            ]
          }
        ]
      }
    ]
  },
  {
    "name": "United States",
    "states": [
      {
        "name": "California",
        "cities": [
          {
            "name": "San Francisco",
            "pincodes": [
              "94107",
              "94103",
              "94105"
            ]
          },
          {
            "name": "San Jose",
            "pincodes": [
              "95113",
              "95134"
            ]
          },
          {
            "name": "Los Angeles",
            "pincodes": [
              "90012",
              "90028"
            ]
          }
        ]
      },
      {
        "name": "Illinois",
        "cities": [
          {
            "name": "Chicago",
            "pincodes": [
              "60601",
              "60611",
              "60606"
            ]
          }
        ]
      },
      {
        "name": "New York",
        "cities": [
          {
            "name": "New York City",
            "pincodes": [
              "10001",
              "10016",
              "10022"
            ]
          }
        ]
      },
      {
        "name": "Texas",
        "cities": [
          {
            "name": "Austin",
            "pincodes": [
              "78701",
              "78704"
            ]
          },
          {
            "name": "Dallas",
            "pincodes": [
              "75201"
            ]
          }
        ]
      },
      {
        "name": "Washington",
        "cities": [
          {
            "name": "Seattle",
            "pincodes": [
              "98101",
              "98109"
            ]
          }
        ]
      }
    ]
  },
  {
    "name": "United Kingdom",
    "states": [
      {
        "name": "England",
        "cities": [
          {
            "name": "London",
            "pincodes": [
              "SW1A 1AA",
              "EC1A 1BB",
              "W1D 3QU"
            ]
          },
          {
            "name": "Manchester",
            "pincodes": [
              "M1 1AD",
              "M2 4WU"
            ]
          },
          {
            "name": "Birmingham",
            "pincodes": [
              "B1 1AA"
            ]
          }
        ]
      }
    ]
  },
  {
    "name": "Germany",
    "states": [
      {
        "name": "Bavaria",
        "cities": [
          {
            "name": "Munich",
            "pincodes": [
              "80331",
              "80802"
            ]
          }
        ]
      },
      {
        "name": "Berlin",
        "cities": [
          {
            "name": "Berlin",
            "pincodes": [
              "10115",
              "10117"
            ]
          }
        ]
      },
      {
        "name": "Hesse",
        "cities": [
          {
            "name": "Frankfurt",
            "pincodes": [
              "60311"
            ]
          }
        ]
      }
    ]
  },
  {
    "name": "Singapore",
    "states": [
      {
        "name": "Singapore",
        "cities": [
          {
            "name": "Singapore",
            "pincodes": [
              "018989",
              "018956",
              "048581"
            ]
          }
        ]
      }
    ]
  },
  {
    "name": "United Arab Emirates",
    "states": [
      {
        "name": "Abu Dhabi",
        "cities": [
          {
            "name": "Abu Dhabi",
            "pincodes": [
              "00000"
            ]
          }
        ]
      },
      {
        "name": "Dubai",
        "cities": [
          {
            "name": "Dubai",
            "pincodes": [
              "00000"
            ]
          }
        ]
      }
    ]
  }
];

export function getCountries(): string[] {
  return COUNTRIES_DATA.map((c) => c.name);
}

export function getStatesForCountry(countryName: string): string[] {
  const country = COUNTRIES_DATA.find((c) => c.name.toLowerCase() === (countryName || '').trim().toLowerCase());
  return country ? country.states.map((s) => s.name) : [];
}

export function getCitiesForState(countryName: string, stateName: string): string[] {
  const country = COUNTRIES_DATA.find((c) => c.name.toLowerCase() === (countryName || '').trim().toLowerCase());
  if (!country) return [];
  const state = country.states.find((s) => s.name.toLowerCase() === (stateName || '').trim().toLowerCase());
  return state ? state.cities.map((ci) => ci.name) : [];
}

export function getPincodesForCity(countryName: string, stateName: string, cityName: string): string[] {
  const country = COUNTRIES_DATA.find((c) => c.name.toLowerCase() === (countryName || '').trim().toLowerCase());
  if (!country) return [];
  const state = country.states.find((s) => s.name.toLowerCase() === (stateName || '').trim().toLowerCase());
  if (!state) return [];
  const city = state.cities.find((ci) => ci.name.toLowerCase() === (cityName || '').trim().toLowerCase());
  return city ? city.pincodes : [];
}

export function findStateForCity(cityName: string, countryName: string = 'India'): string | undefined {
  const country = COUNTRIES_DATA.find((c) => c.name.toLowerCase() === (countryName || '').trim().toLowerCase());
  if (!country) return undefined;
  for (const s of country.states) {
    if (s.cities.some((ci) => ci.name.toLowerCase() === (cityName || '').trim().toLowerCase())) {
      return s.name;
    }
  }
  return undefined;
}
