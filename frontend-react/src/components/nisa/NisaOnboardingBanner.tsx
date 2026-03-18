import { Link } from "react-router-dom"
import { Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

interface NisaOnboardingBannerProps {
  onLearnMore?: () => void
}

export function NisaOnboardingBanner({ onLearnMore }: NisaOnboardingBannerProps) {
  const { t } = useTranslation()

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardContent className="pt-6 space-y-4">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-primary/15 p-2">
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold">{t("nisa.onboarding.title")}</p>
            <p className="text-xs text-muted-foreground">{t("nisa.onboarding.description")}</p>
          </div>
        </div>
        <ol className="space-y-1 pl-5 text-xs text-muted-foreground list-decimal">
          <li>{t("nisa.onboarding.step1")}</li>
          <li>{t("nisa.onboarding.step2")}</li>
          <li>{t("nisa.onboarding.step3")}</li>
        </ol>
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm">
            <Link to="/allocation?tab=accounts">{t("nisa.onboarding.create_account")}</Link>
          </Button>
          <Button size="sm" variant="outline" onClick={onLearnMore}>
            {t("nisa.onboarding.learn_more")}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
