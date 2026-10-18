import { Container } from "@/components/layout/Container";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Illustration } from "@/components/ui/Illustration";

const copy = {
  title: "Тут лише пустота… як у Краю",
  text: "Сторінку не знайдено. Можливо, її перенесли або видалили.",
  home: "На головну",
};

export default function NotFound() {
  return (
    <Container className="flex flex-1 flex-col items-center justify-center gap-8 py-24 text-center">
      <Illustration name="void" size={160} />
      <h1 className="text-h1">{copy.title}</h1>
      <p className="max-w-prose text-muted">{copy.text}</p>
      <ButtonLink href="/" size="lg">
        {copy.home}
      </ButtonLink>
    </Container>
  );
}
