const currentYear = new Date().getFullYear();

export const YEARS = [];
for (let y = currentYear; y >= 2000; y -= 1) {
  YEARS.push(y);
}

export const BODY_TYPES = [
  "Sedan",
  "Hatchback",
  "SUV",
  "Wagon",
  "Coupe",
  "Convertible",
  "Van",
  "Pickup",
];

export const COLORS = [
  "Black",
  "White",
  "Silver",
  "Gray",
  "Blue",
  "Red",
  "Green",
  "Orange",
  "Brown",
  "Beige",
];

export const STATUS_LABELS = {
  created: "Принято",
  processing: "Оценивается (enrichment + ML)",
  ready: "Готово к аукциону",
  failed: "Ошибка оценки",
};
