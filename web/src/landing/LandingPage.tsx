import { Footer } from './Footer'
import { Hero } from './Hero'
import { HowItWorks } from './HowItWorks'
import { ProblemCards } from './ProblemCards'
import { Results } from './Results'
import { SafetyGuarantee } from './SafetyGuarantee'

export function LandingPage() {
  return (
    <div className="min-h-svh bg-[#0f2a4d]">
      <Hero />
      <ProblemCards />
      <HowItWorks />
      <SafetyGuarantee />
      <Results />
      <Footer />
    </div>
  )
}
