"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Popover } from "@/components/ui/Popover";
import { Sheet } from "@/components/ui/Sheet";
import { useToast } from "@/components/ui/useToast";

/** Dialog, Sheet, Popover and Toast with working triggers. */
export function OverlayDemos() {
  const toast = useToast();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="flex flex-wrap gap-3">
      <Dialog
        title="Нова колекція"
        description="Назви колекцію — потім додаси до неї моди, скіни й сервери."
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        trigger={<Button variant="secondary">Dialog</Button>}
        footer={
          <>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>
              Скасувати
            </Button>
            <Button onClick={() => setDialogOpen(false)}>Створити</Button>
          </>
        }
      >
        <Input label="Назва" placeholder="Мій сетап на 1.21" />
      </Dialog>

      <Sheet title="Фільтри" trigger={<Button variant="secondary">Sheet</Button>}>
        <p className="text-muted">Шторка знизу для фільтрів і дій на телефоні.</p>
      </Sheet>

      <Popover label="Додати в колекцію" trigger={<Button variant="secondary">Popover</Button>}>
        <p className="text-sm">Список колекцій з галочками з’явиться на етапі 4.</p>
      </Popover>

      <Button
        variant="secondary"
        onClick={() => toast({ title: "Збережено", description: "Мод додано в обране." })}
      >
        Toast
      </Button>
      <Button
        variant="secondary"
        onClick={() =>
          toast({ title: "Не вдалося зберегти", description: "Перевір з’єднання.", tone: "danger" })
        }
      >
        Toast · помилка
      </Button>
    </div>
  );
}
