/**
 * HemoNexus Smart Requirement-Based Matching Engine
 * Implements blood group compatibility matrices and multi-factor heuristic ranking.
 */

const HemoMatcher = (() => {
  // ABO and Rh Compatibility Matrix
  const RED_BLOOD_CELL_COMPATIBILITY = {
    'O-': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'], // Universal donor
    'O+': ['O+', 'A+', 'B+', 'AB+'],
    'A-': ['A-', 'A+', 'AB-', 'AB+'],
    'A+': ['A+', 'AB+'],
    'B-': ['B-', 'B+', 'AB-', 'AB+'],
    'B+': ['B+', 'AB+'],
    'AB-': ['AB-', 'AB+'],
    'AB+': ['AB+'] // Universal recipient
  };

  const PLASMA_PLATELET_COMPATIBILITY = {
    'AB+': ['AB+', 'AB-', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-'], // Universal plasma donor
    'AB-': ['AB+', 'AB-', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-'],
    'A+': ['A+', 'A-', 'O+', 'O-'],
    'A-': ['A+', 'A-', 'O+', 'O-'],
    'B+': ['B+', 'B-', 'O+', 'O-'],
    'B-': ['B+', 'B-', 'O+', 'O-'],
    'O+': ['O+', 'O-'],
    'O-': ['O+', 'O-']
  };

  /**
   * Check if a donor blood group can donate to recipient blood group for a given component.
   */
  const isCompatible = (donorGroup, recipientGroup, component = 'Whole Blood') => {
    if (!donorGroup || !recipientGroup) return false;
    
    if (component === 'Plasma' || component === 'Platelets') {
      const allowedRecipients = PLASMA_PLATELET_COMPATIBILITY[donorGroup] || [];
      return allowedRecipients.includes(recipientGroup);
    } else {
      // Whole Blood or RBC
      const allowedRecipients = RED_BLOOD_CELL_COMPATIBILITY[donorGroup] || [];
      return allowedRecipients.includes(recipientGroup);
    }
  };

  /**
   * Calculate Days between today and last donation date
   */
  const getDaysSinceDonation = (lastDonatedDateStr) => {
    if (!lastDonatedDateStr) return 999;
    const lastDate = new Date(lastDonatedDateStr);
    const today = new Date('2026-08-27');
    const diffTime = Math.abs(today - lastDate);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  /**
   * Compute multi-factor match score and detailed ranking breakdown
   */
  const rankDonor = (donor, requirement) => {
    const { recipientGroup, component = 'Whole Blood', maxDistanceKm = 15 } = requirement;

    // 1. Compatibility Check
    const compatible = isCompatible(donor.bloodGroup, recipientGroup, component);
    if (!compatible) {
      return { donor, matchScore: 0, isCompatible: false, reasons: ['Incompatible blood antigen group'] };
    }

    const reasons = [];

    // Antigen Match Score (Weight: 40%)
    let antigenScore = 0;
    if (donor.bloodGroup === recipientGroup) {
      antigenScore = 100;
      reasons.push(`Exact Blood Group Match (${donor.bloodGroup})`);
    } else {
      antigenScore = 85;
      reasons.push(`Clinically Compatible (${donor.bloodGroup} → ${recipientGroup})`);
    }

    // Distance / Proximity Score (Weight: 30%)
    const dist = parseFloat(donor.distanceKm) || 5.0;
    let distanceScore = 0;
    if (dist <= 3) {
      distanceScore = 100;
      reasons.push(`Very Close Proximity (${dist} km, ~10 mins ETA)`);
    } else if (dist <= 7) {
      distanceScore = 85;
      reasons.push(`Nearby Location (${dist} km, ~20 mins ETA)`);
    } else if (dist <= maxDistanceKm) {
      distanceScore = 65;
      reasons.push(`Within radius (${dist} km)`);
    } else {
      distanceScore = 40;
    }

    // Cooldown / Eligibility Recency Score (Weight: 20%)
    const daysSince = getDaysSinceDonation(donor.lastDonatedDate);
    let eligibilityScore = 0;
    if (donor.status === 'available' && daysSince >= 90) {
      eligibilityScore = 100;
      reasons.push(`Fully Eligible (Last donated ${daysSince} days ago)`);
    } else if (donor.status === 'in-transit') {
      eligibilityScore = 50;
      reasons.push('Currently In-Transit');
    } else {
      eligibilityScore = 20;
      reasons.push(`In 90-day cooldown (${daysSince}/90 days)`);
    }

    // Reliability & Historical Response Rate (Weight: 10%)
    const responseScore = donor.responseRate || 90;
    if (responseScore >= 95) {
      reasons.push(`High Reliability (${responseScore}% response rate)`);
    }

    if (donor.verified) {
      reasons.push('Verified Healthcare KYC');
    }

    // Weighted Formula
    const finalScore = Math.round(
      (antigenScore * 0.40) +
      (distanceScore * 0.30) +
      (eligibilityScore * 0.20) +
      (responseScore * 0.10)
    );

    return {
      donor,
      matchScore: finalScore,
      isCompatible: true,
      antigenScore,
      distanceScore,
      eligibilityScore,
      responseScore,
      reasons
    };
  };

  /**
   * Find and rank all donors for a given requirement
   */
  const findMatches = (requirement, donorList = null) => {
    const donors = donorList || (typeof HemoStore !== 'undefined' ? HemoStore.getDonors() : []);
    
    const results = donors
      .map(donor => rankDonor(donor, requirement))
      .filter(res => res.isCompatible && res.matchScore > 40)
      .sort((a, b) => b.matchScore - a.matchScore);

    return results;
  };

  return {
    isCompatible,
    rankDonor,
    findMatches,
    RED_BLOOD_CELL_COMPATIBILITY,
    PLASMA_PLATELET_COMPATIBILITY
  };
})();
