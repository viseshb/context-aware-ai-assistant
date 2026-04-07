import LandingNavbar from "@/components/landing/LandingNavbar";
import HeroSection from "@/components/landing/HeroSection";
import FeaturesGrid from "@/components/landing/FeaturesGrid";
import HowItWorks from "@/components/landing/HowItWorks";
import SecurityBadges from "@/components/landing/SecurityBadges";
import CTAFooter from "@/components/landing/CTAFooter";
import Footer from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <>
      <LandingNavbar />
      <HeroSection />
      <FeaturesGrid />
      <HowItWorks />
      <SecurityBadges />
      <CTAFooter />
      <Footer />
    </>
  );
}
