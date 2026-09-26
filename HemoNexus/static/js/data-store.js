/**
 * HemoNexus Data Store
 * Reactive in-memory and LocalStorage mock store for donors, blood requests, and logs.
 */

const HemoStore = (() => {
  const STORAGE_KEYS = {
    DONORS: 'hemonexus_donors',
    REQUESTS: 'hemonexus_requests',
    ACTIVITIES: 'hemonexus_activities'
  };

  const DEFAULT_DONORS = [
    {
      id: 'D-101',
      name: 'Aarav Sharma',
      bloodGroup: 'O-',
      gender: 'Male',
      age: 29,
      phone: '+91 98765 43210',
      email: 'aarav.sharma@example.com',
      city: 'Mumbai',
      area: 'Andheri West',
      distanceKm: 2.4,
      status: 'available', // available, cooldown, in-transit, unavailable
      verified: true,
      lastDonatedDate: '2026-04-10',
      totalDonations: 12,
      responseRate: 98,
      eligibleComponents: ['Whole Blood', 'RBC', 'Platelets'],
      hemoglobin: '15.2 g/dL',
      weightKg: 74,
      bloodPressure: '120/80 mmHg'
    },
    {
      id: 'D-102',
      name: 'Pooja Nair',
      bloodGroup: 'A+',
      gender: 'Female',
      age: 26,
      phone: '+91 98123 45678',
      email: 'pooja.nair@example.com',
      city: 'Mumbai',
      area: 'Bandra West',
      distanceKm: 4.1,
      status: 'available',
      verified: true,
      lastDonatedDate: '2026-03-15',
      totalDonations: 8,
      responseRate: 95,
      eligibleComponents: ['Whole Blood', 'Plasma', 'Platelets'],
      hemoglobin: '13.8 g/dL',
      weightKg: 62,
      bloodPressure: '118/76 mmHg'
    },
    {
      id: 'D-103',
      name: 'Rohan Deshmukh',
      bloodGroup: 'B+',
      gender: 'Male',
      age: 34,
      phone: '+91 97654 32109',
      email: 'rohan.d@example.com',
      city: 'Mumbai',
      area: 'Powai',
      distanceKm: 7.8,
      status: 'cooldown',
      verified: true,
      lastDonatedDate: '2026-07-28',
      totalDonations: 15,
      responseRate: 92,
      eligibleComponents: ['Whole Blood', 'RBC'],
      hemoglobin: '14.6 g/dL',
      weightKg: 80,
      bloodPressure: '122/82 mmHg'
    },
    {
      id: 'D-104',
      name: 'Ananya Sengupta',
      bloodGroup: 'AB+',
      gender: 'Female',
      age: 24,
      phone: '+91 98450 11223',
      email: 'ananya.s@example.com',
      city: 'Mumbai',
      area: 'Dadar',
      distanceKm: 3.5,
      status: 'available',
      verified: true,
      lastDonatedDate: '2026-02-18',
      totalDonations: 6,
      responseRate: 100,
      eligibleComponents: ['Plasma', 'Platelets'],
      hemoglobin: '13.4 g/dL',
      weightKg: 58,
      bloodPressure: '116/74 mmHg'
    },
    {
      id: 'D-105',
      name: 'Vikram Mehta',
      bloodGroup: 'O+',
      gender: 'Male',
      age: 38,
      phone: '+91 98200 99887',
      email: 'vikram.m@example.com',
      city: 'Mumbai',
      area: 'Juhu',
      distanceKm: 1.8,
      status: 'available',
      verified: true,
      lastDonatedDate: '2026-05-02',
      totalDonations: 21,
      responseRate: 99,
      eligibleComponents: ['Whole Blood', 'RBC', 'Platelets'],
      hemoglobin: '15.8 g/dL',
      weightKg: 84,
      bloodPressure: '124/80 mmHg'
    },
    {
      id: 'D-106',
      name: 'Kavita Patel',
      bloodGroup: 'AB-',
      gender: 'Female',
      age: 31,
      phone: '+91 98980 44556',
      email: 'kavita.p@example.com',
      city: 'Mumbai',
      area: 'Goregaon',
      distanceKm: 6.2,
      status: 'available',
      verified: true,
      lastDonatedDate: '2026-01-20',
      totalDonations: 9,
      responseRate: 90,
      eligibleComponents: ['Plasma', 'Platelets', 'Whole Blood'],
      hemoglobin: '13.1 g/dL',
      weightKg: 65,
      bloodPressure: '120/78 mmHg'
    },
    {
      id: 'D-107',
      name: 'Sameer Khan',
      bloodGroup: 'A-',
      gender: 'Male',
      age: 27,
      phone: '+91 98333 77889',
      email: 'sameer.k@example.com',
      city: 'Mumbai',
      area: 'Kurla',
      distanceKm: 5.5,
      status: 'in-transit',
      verified: false,
      lastDonatedDate: '2026-04-25',
      totalDonations: 4,
      responseRate: 88,
      eligibleComponents: ['Whole Blood', 'RBC'],
      hemoglobin: '14.9 g/dL',
      weightKg: 70,
      bloodPressure: '118/80 mmHg'
    }
  ];

  const DEFAULT_REQUESTS = [
    {
      id: 'REQ-4091',
      patientName: 'Kunal Singhania',
      bloodGroup: 'O-',
      component: 'Whole Blood',
      unitsNeeded: 3,
      unitsFulfilled: 2,
      hospital: 'Lilavati Hospital & Research Centre',
      location: 'Bandra, Mumbai',
      urgency: 'critical', // critical, urgent, routine
      status: 'in-progress', // pending, matched, in-progress, fulfilled
      requiredBy: '2026-08-27 04:00 AM',
      createdAt: '2026-08-26 23:15',
      contactPerson: 'Dr. R. Kulkarni (ICU Lead)',
      contactPhone: '+91 98222 00112',
      notes: 'Emergency cardiac bypass surgery in progress. Universal O- required urgently.'
    },
    {
      id: 'REQ-4092',
      patientName: 'Sneha Verma',
      bloodGroup: 'A+',
      component: 'Platelets',
      unitsNeeded: 2,
      unitsFulfilled: 1,
      hospital: 'Tata Memorial Hospital',
      location: 'Parel, Mumbai',
      urgency: 'urgent',
      status: 'matched',
      requiredBy: '2026-08-27 10:00 AM',
      createdAt: '2026-08-26 21:30',
      contactPerson: 'Aditya Verma (Husband)',
      contactPhone: '+91 98111 22334',
      notes: 'Thrombocytopenia management. Single donor platelets preferred.'
    },
    {
      id: 'REQ-4093',
      patientName: 'Devendra Joshi',
      bloodGroup: 'B+',
      component: 'RBC',
      unitsNeeded: 2,
      unitsFulfilled: 2,
      hospital: 'Kokilaben Dhirubhai Ambani Hospital',
      location: 'Andheri West, Mumbai',
      urgency: 'routine',
      status: 'fulfilled',
      requiredBy: '2026-08-27 02:00 PM',
      createdAt: '2026-08-26 14:00',
      contactPerson: 'Sunita Joshi',
      contactPhone: '+91 98333 44556',
      notes: 'Scheduled orthopedic joint replacement.'
    }
  ];

  const DEFAULT_ACTIVITIES = [
    {
      id: 'act-1',
      title: 'Donor Dispatch Confirmed',
      desc: 'Aarav Sharma accepted emergency request REQ-4091 for Lilavati Hospital.',
      time: '12 mins ago',
      type: 'dispatch',
      icon: 'fa-truck-medical',
      iconClass: 'stat-icon-primary'
    },
    {
      id: 'act-2',
      title: 'New Blood Request Registered',
      desc: 'Emergency O- Whole Blood request logged by Lilavati ICU.',
      time: '45 mins ago',
      type: 'request',
      icon: 'fa-droplet',
      iconClass: 'stat-icon-danger'
    },
    {
      id: 'act-3',
      title: 'Donation Completed & Verified',
      desc: 'Devendra Joshi request fulfilled with 2 units of B+ RBC.',
      time: '2 hours ago',
      type: 'fulfilled',
      icon: 'fa-circle-check',
      iconClass: 'stat-icon-success'
    }
  ];

  // Helper functions
  const get = (key, fallback) => {
    try {
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : fallback;
    } catch (e) {
      console.warn('LocalStorage access issue:', e);
      return fallback;
    }
  };

  const set = (key, val) => {
    try {
      localStorage.setItem(key, JSON.stringify(val));
    } catch (e) {
      console.warn('LocalStorage save issue:', e);
    }
  };

  return {
    getDonors: () => get(STORAGE_KEYS.DONORS, DEFAULT_DONORS),
    getDonorById: (id) => {
      const donors = get(STORAGE_KEYS.DONORS, DEFAULT_DONORS);
      return donors.find(d => d.id === id) || donors[0];
    },
    addDonor: (donor) => {
      const donors = get(STORAGE_KEYS.DONORS, DEFAULT_DONORS);
      const newDonor = {
        ...donor,
        id: `D-${100 + donors.length + 1}`,
        verified: true,
        totalDonations: 0,
        responseRate: 100,
        distanceKm: (Math.random() * 5 + 1).toFixed(1)
      };
      donors.unshift(newDonor);
      set(STORAGE_KEYS.DONORS, donors);
      return newDonor;
    },
    getRequests: () => get(STORAGE_KEYS.REQUESTS, DEFAULT_REQUESTS),
    addRequest: (req) => {
      const requests = get(STORAGE_KEYS.REQUESTS, DEFAULT_REQUESTS);
      const newReq = {
        ...req,
        id: `REQ-${4000 + requests.length + 100}`,
        status: 'pending',
        unitsFulfilled: 0,
        createdAt: 'Just now'
      };
      requests.unshift(newReq);
      set(STORAGE_KEYS.REQUESTS, requests);
      return newReq;
    },
    getActivities: () => get(STORAGE_KEYS.ACTIVITIES, DEFAULT_ACTIVITIES),
    logActivity: (activity) => {
      const acts = get(STORAGE_KEYS.ACTIVITIES, DEFAULT_ACTIVITIES);
      acts.unshift({
        id: `act-${Date.now()}`,
        time: 'Just now',
        ...activity
      });
      set(STORAGE_KEYS.ACTIVITIES, acts.slice(0, 20));
    }
  };
})();
