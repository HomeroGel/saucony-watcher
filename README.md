# saucony-watcher

Avisa por email cuando la Saucony Endorphin Azura White/Navy entra en descuento
en talle AR 43 (US 10), en saucony.com.ar. Corre en GitHub Actions, no depende
de tu máquina ni de Claude.

Cómo funciona: cada ~30 minutos un workflow de GitHub Actions baja la página
del producto, lee el JSON interno de Tienda Nube (precio, precio tachado y
stock por talle) y, si detecta que pasó de "sin descuento" a "con descuento y
stock", te manda un email. El estado se guarda en `state.json`, que el propio
workflow commitea, para no reenviar el mismo aviso en cada corrida.

## 1. Generar una contraseña de aplicación de Gmail

1. Entrá a tu cuenta de Google y activá la verificación en 2 pasos si no la
   tenés (myaccount.google.com/security).
2. Andá a https://myaccount.google.com/apppasswords
3. Creá una contraseña de aplicación (podés llamarla "saucony-watcher").
   Te va a dar un código de 16 caracteres. Ese es tu `SMTP_PASS`.

## 2. Crear el repo en GitHub

Desde esta carpeta (`saucony-watcher`), ya está inicializado un repo git local
con el primer commit. Para subirlo:

```bash
# Creá un repo vacío en https://github.com/new (sin README, sin .gitignore)
# y después:
git remote add origin https://github.com/TU_USUARIO/saucony-watcher.git
git branch -M main
git push -u origin main
```

(O usá `gh repo create saucony-watcher --private --source=. --push` si tenés
la GitHub CLI instalada y autenticada.)

## 3. Cargar los secrets

En el repo de GitHub: **Settings → Secrets and variables → Actions → New
repository secret**. Cargá:

| Secret       | Valor                                                        |
|--------------|---------------------------------------------------------------|
| `SMTP_HOST`  | `smtp.gmail.com`                                               |
| `SMTP_PORT`  | `587`                                                          |
| `SMTP_USER`  | tu dirección de Gmail (la que genera la contraseña de app)     |
| `SMTP_PASS`  | la contraseña de aplicación de 16 caracteres del paso 1       |
| `EMAIL_TO`   | `homerogelves@gmail.com`                                       |

## 4. Permisos de escritura del workflow

En **Settings → Actions → General → Workflow permissions**, elegí
**"Read and write permissions"**. Esto es necesario para que el workflow
pueda commitear `state.json` después de cada corrida.

## 5. Probarlo

En la pestaña **Actions** del repo, entrá al workflow "Check Saucony
discount" y tocá **"Run workflow"** para dispararlo a mano. Mirá el log del
step "Run check": va a imprimir el talle, precio, precio tachado, stock y si
detectó oferta o no. Si todo sale bien ahí, el cron (`cron: "7,37 * * * *"`,
cada ~30 min) se va a encargar de correrlo solo de ahí en más.

Para forzar un email de prueba sin esperar a que el producto entre en oferta
de verdad, podés editar a mano `state.json` (poné `"on_sale": false`) y
correr el workflow en un momento en que el producto SÍ tenga `compare_at_price`
distinto de null — o, más simple, cambiá momentáneamente en `check_saucony.py`
la condición de `is_on_sale` para que devuelva `True` siempre, corré el
workflow una vez, y después revertí el cambio.

## Si querés vigilar otro producto o talle

Editá las constantes al principio de `check_saucony.py`:

- `PRODUCT_URL`: la URL del producto.
- `TARGET_SIZE_PREFIX`: el prefijo del talle tal como aparece en `option1`
  (por ejemplo `"US 10"` para AR 43 en este producto — cada tienda puede
  nombrar los talles distinto).

## Limitaciones conocidas

- Depende de que la tienda siga siendo Tienda Nube y exponga
  `LS.variants = [...]` en el HTML con esta forma. Si Saucony cambia de
  plataforma o de tema, el script va a fallar con un error claro en el log
  de Actions (y GitHub te manda un email automático cuando un workflow
  falla, así te enterás igual).
- Los crons de GitHub Actions son "best effort": en momentos de mucha carga
  pueden retrasarse varios minutos. Para este caso de uso no importa.
- El repo debería ser privado si no querés que se vea públicamente qué
  producto estás vigilando.
