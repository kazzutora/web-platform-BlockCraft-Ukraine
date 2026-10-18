import { FormPage } from "@/components/layout/FormPage";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

export default function FormTemplatePage() {
  return (
    <FormPage
      title="Додати сервер"
      description="Ми перевіримо, що сервер відповідає, і покажемо онлайн."
    >
      <form className="flex flex-col gap-6">
        <Input label="Назва" placeholder="UA Survival" required />
        <Input
          label="Адреса"
          placeholder="play.example.ua"
          hint="Домен або IP, порт — окремо"
          required
        />
        <Input label="Порт" type="number" defaultValue={25565} />
        <Select
          label="Видання"
          options={[
            { value: "java", label: "Java" },
            { value: "bedrock", label: "Bedrock" },
            { value: "both", label: "Java і Bedrock" },
          ]}
        />
        <Button type="submit" size="lg">
          Додати сервер
        </Button>
      </form>
    </FormPage>
  );
}
