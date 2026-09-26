// Номер версии игры. Его знает сервер (берёт из pyproject.toml); спрашиваем один раз на всю игру.
// Показывается в меню и на игровом экране — чтобы не путать, какая версия открыта.

export const gameVersion = fetch('api/version')
  .then((response) => response.json())
  .then(({ version }) => version)
  .catch(() => '');
