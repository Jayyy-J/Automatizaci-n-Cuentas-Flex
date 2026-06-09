import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from config import config
import database
from persistence import PostgresPersistence

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados del ConversationHandler
(
    MENU_PRINCIPAL,
    CREAR_CORREO,
    CREAR_PASS,
    CREAR_FOTO,
    CREAR_ESTADO,
    SEGUIMIENTO_MENU,
    SEGUIMIENTO_CORREO,
    SEGUIMIENTO_PASS,
    SEGUIMIENTO_ACCIONES,
    SEGUIMIENTO_VALOR_VENTA,
    SEGUIMIENTO_DATOS_PAGO
) = range(11)

# Teclados
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Crear Cuenta", callback_data='menu_crear')],
        [InlineKeyboardButton("Seguimiento", callback_data='menu_seguimiento')],
        [InlineKeyboardButton("Cuentas para Venta", callback_data='menu_venta')],
        [InlineKeyboardButton("Cuentas a Despachar", callback_data='menu_despachar')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Volver al menú principal", callback_data='volver_menu')]])

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "Bienvenido al Gestor de Inventario. Seleccione una opción:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "Bienvenido al Gestor de Inventario. Seleccione una opción:",
            reply_markup=get_main_menu_keyboard()
        )
    return MENU_PRINCIPAL

async def menu_crear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Por favor, ingresa el Correo de la cuenta:")
    return CREAR_CORREO

async def menu_seguimiento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Ingresar Datos", callback_data='seg_ingresar')],
        [InlineKeyboardButton("Volver al menú", callback_data='volver_menu')]
    ]
    await query.edit_message_text("Seguimiento de cuenta. ¿Qué desea hacer?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SEGUIMIENTO_MENU

async def menu_venta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cuentas = database.listar_cuentas_venta()
    if not cuentas:
        mensaje = "No hay cuentas listas para comercializar."
    else:
        mensaje = "Cuentas para Venta:\n\n"
        for c in cuentas:
            mensaje += f"📧 Correo: {c['correo']}\n🔑 Pass: {c['contrasena']}\n-------------------\n"

    await query.edit_message_text(mensaje, reply_markup=get_back_to_menu_keyboard())
    return MENU_PRINCIPAL

async def menu_despachar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Esta fase está en desarrollo", reply_markup=get_back_to_menu_keyboard())
    return MENU_PRINCIPAL

# Flujo Crear Cuenta
async def crear_correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nuevo_correo'] = update.message.text
    await update.message.reply_text("Ingresa la Contraseña:")
    return CREAR_PASS

async def crear_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nuevo_pass'] = update.message.text
    await update.message.reply_text("Envía la Foto de la licencia:")
    return CREAR_FOTO

async def crear_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Por favor, envía una foto.")
        return CREAR_FOTO

    context.user_data['nuevo_foto_id'] = update.message.photo[-1].file_id
    keyboard = [
        [InlineKeyboardButton("En Proceso", callback_data='estado_en_proceso')],
        [InlineKeyboardButton("Completado", callback_data='estado_completado')],
        [InlineKeyboardButton("Subir Datos de Pago", callback_data='estado_subir_datos_pago')],
        [InlineKeyboardButton("Lista para Comercializar", callback_data='estado_lista_para_comercializar')]
    ]
    await update.message.reply_text("Selecciona el estado inicial:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CREAR_ESTADO

async def crear_estado_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estado = query.data.replace('estado_', '')

    try:
        database.registrar_cuenta(
            context.user_data['nuevo_correo'],
            context.user_data['nuevo_pass'],
            context.user_data['nuevo_foto_id'],
            estado
        )
        await query.edit_message_text(f"Cuenta registrada con éxito en estado: {estado}")
    except Exception as e:
        logger.error(f"Error registrando cuenta: {e}")
        await query.edit_message_text("Hubo un error al registrar la cuenta. Asegúrate de que el correo no esté duplicado.")

    # Volver al menú principal
    await query.message.reply_text("Seleccione una opción:", reply_markup=get_main_menu_keyboard())
    return MENU_PRINCIPAL

# Flujo Seguimiento
async def seg_ingresar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ingresa el Correo de la cuenta a buscar:")
    return SEGUIMIENTO_CORREO

async def seg_correo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['busqueda_correo'] = update.message.text
    await update.message.reply_text("Ingresa la Contraseña para confirmar:")
    return SEGUIMIENTO_PASS

async def seg_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    correo = context.user_data['busqueda_correo']
    contrasena = update.message.text
    cuenta = database.get_cuenta_por_correo_y_pass(correo, contrasena)

    if not cuenta:
        await update.message.reply_text("Cuenta no encontrada o datos incorrectos.", reply_markup=get_back_to_menu_keyboard())
        return MENU_PRINCIPAL

    context.user_data['cuenta_actual'] = correo
    mensaje = (
        f"Información de la cuenta:\n"
        f"📧 Correo: {cuenta['correo']}\n"
        f"📍 Estado actual: {cuenta['estado']}\n"
        f"💰 Valor venta: {cuenta['valor_venta']}\n"
    )

    keyboard = [
        [InlineKeyboardButton("En Proceso", callback_data='mod_en_proceso')],
        [InlineKeyboardButton("Completado", callback_data='mod_completado')],
        [InlineKeyboardButton("Subir Datos de Pago", callback_data='mod_subir_datos_pago')],
        [InlineKeyboardButton("Lista para Comercializar", callback_data='mod_lista_para_comercializar')],
        [InlineKeyboardButton("Cuenta Vendida", callback_data='mod_vendida')],
        [InlineKeyboardButton("Volver", callback_data='volver_menu')]
    ]

    await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
    return SEGUIMIENTO_ACCIONES

async def mod_estado_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nuevo_estado = query.data.replace('mod_', '')
    correo = context.user_data.get('cuenta_actual')

    if nuevo_estado == 'vendida':
        await query.edit_message_text("Por favor, escribe el valor de la venta:")
        return SEGUIMIENTO_VALOR_VENTA

    if nuevo_estado == 'subir_datos_pago':
        await query.edit_message_text("Por favor, ingresa los datos de pago:")
        return SEGUIMIENTO_DATOS_PAGO

    database.actualizar_estado_cuenta(correo, nuevo_estado)
    await query.edit_message_text(f"Estado actualizado a: {nuevo_estado}")
    await query.message.reply_text("Seleccione una opción:", reply_markup=get_main_menu_keyboard())
    return MENU_PRINCIPAL

async def seg_valor_venta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valor = update.message.text
    correo = context.user_data.get('cuenta_actual')

    try:
        # Intentar convertir a número
        valor_num = float(valor)
        database.registrar_valor_venta(correo, valor_num)
        await update.message.reply_text(f"Cuenta marcada como vendida por un valor de {valor_num}.")
    except ValueError:
        await update.message.reply_text("Por favor, ingresa un número válido para el valor de venta.")
        return SEGUIMIENTO_VALOR_VENTA
    except Exception as e:
        logger.error(f"Error al registrar valor venta: {e}")
        await update.message.reply_text("Ocurrió un error al actualizar la cuenta.")

    await update.message.reply_text("Seleccione una opción:", reply_markup=get_main_menu_keyboard())
    return MENU_PRINCIPAL

async def seg_datos_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos = update.message.text
    correo = context.user_data.get('cuenta_actual')

    try:
        database.agregar_datos_pago(correo, datos)
        database.actualizar_estado_cuenta(correo, 'subir_datos_pago')
        await update.message.reply_text("Datos de pago actualizados correctamente.")
    except Exception as e:
        logger.error(f"Error al agregar datos de pago: {e}")
        await update.message.reply_text("Ocurrió un error al actualizar los datos de pago.")

    await update.message.reply_text("Seleccione una opción:", reply_markup=get_main_menu_keyboard())
    return MENU_PRINCIPAL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.", reply_markup=get_main_menu_keyboard())
    return MENU_PRINCIPAL

def main():
    # Inicializar base de datos
    database.init_db()

    # Validar config
    try:
        config.validate()
    except ValueError as e:
        logger.error(e)
        return

    # Construir la aplicación con persistencia
    persistence = PostgresPersistence()
    application = Application.builder().token(config.TELEGRAM_TOKEN).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU_PRINCIPAL: [
                CallbackQueryHandler(menu_crear, pattern='^menu_crear$'),
                CallbackQueryHandler(menu_seguimiento, pattern='^menu_seguimiento$'),
                CallbackQueryHandler(menu_venta, pattern='^menu_venta$'),
                CallbackQueryHandler(menu_despachar, pattern='^menu_despachar$'),
                CallbackQueryHandler(start, pattern='^volver_menu$')
            ],
            CREAR_CORREO: [MessageHandler(filters.TEXT & ~filters.COMMAND, crear_correo)],
            CREAR_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, crear_pass)],
            CREAR_FOTO: [MessageHandler(filters.PHOTO, crear_foto)],
            CREAR_ESTADO: [CallbackQueryHandler(crear_estado_callback, pattern='^estado_')],
            SEGUIMIENTO_MENU: [
                CallbackQueryHandler(seg_ingresar_callback, pattern='^seg_ingresar$'),
                CallbackQueryHandler(start, pattern='^volver_menu$')
            ],
            SEGUIMIENTO_CORREO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seg_correo)],
            SEGUIMIENTO_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, seg_pass)],
            SEGUIMIENTO_ACCIONES: [
                CallbackQueryHandler(mod_estado_callback, pattern='^mod_'),
                CallbackQueryHandler(start, pattern='^volver_menu$')
            ],
            SEGUIMIENTO_VALOR_VENTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, seg_valor_venta)],
            SEGUIMIENTO_DATOS_PAGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seg_datos_pago)]
        },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^volver_menu$')],
        name="inventario_conv",
        persistent=True
    )

    application.add_handler(conv_handler)

    # Iniciar el bot
    application.run_polling()

if __name__ == '__main__':
    main()
