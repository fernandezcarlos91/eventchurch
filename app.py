# app.py - EventChurch - Hito 3 (Completo)

from flask import Flask, render_template, jsonify, request, abort
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# ==============================================================
# CONFIGURACIÓN DE BASE DE DATOS (phpMyAdmin)
# ==============================================================

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '',
    'database': 'eventchurch',
    'charset': 'utf8mb4'
}

# ==============================================================
# FUNCIONES AUXILIARES - Conexión a MySQL
# ==============================================================

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error de conexión: {e}")
        return None

def query(sql, params=(), one=False):
    """Ejecuta SELECT y retorna filas como diccionarios"""
    conn = get_db_connection()
    if conn is None:
        return None if one else []
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    
    if one:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return result

def execute(sql, params=()):
    """Ejecuta INSERT, UPDATE o DELETE"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    
    lastrowid = cursor.lastrowid
    cursor.close()
    conn.close()
    return lastrowid

# ==============================================================
# FUNCIONES AUXILIARES - Lógica de negocio
# ==============================================================

def calcular_progreso(evento_id):
    """Calcula el porcentaje de avance de un evento"""
    tareas = query(
        "SELECT COUNT(*) as total, SUM(completada) as completadas FROM tareas WHERE evento_id = %s",
        (evento_id,),
        one=True
    )
    if tareas is None or tareas['total'] == 0:
        return 0
    completadas = tareas['completadas'] or 0
    return round((completadas / tareas['total']) * 100, 0)

def obtener_evento_con_progreso(evento):
    """Agrega el campo porcentaje_avance a un evento"""
    evento_con_progreso = dict(evento)
    evento_con_progreso['porcentaje_avance'] = calcular_progreso(evento['id'])
    return evento_con_progreso

# ==============================================================
# RUTAS HTML - Página de inicio
# ==============================================================

@app.route('/')
def inicio():
    """Página de inicio con estadísticas"""
    eventos = query("SELECT * FROM eventos")
    tareas = query("SELECT * FROM tareas")
    
    total_eventos = len(eventos)
    total_tareas = len(tareas)
    tareas_completadas = sum(1 for t in tareas if t['completada'])
    
    if total_tareas > 0:
        porcentaje_global = round((tareas_completadas / total_tareas) * 100, 0)
    else:
        porcentaje_global = 0
    
    return render_template('inicio.html',
        titulo='Inicio',
        total_eventos=total_eventos,
        total_tareas=total_tareas,
        tareas_completadas=tareas_completadas,
        porcentaje_global=porcentaje_global,
        eventos=eventos
    )

# ==============================================================
# RUTAS HTML - Lista de eventos (CRUD - Read)
# ==============================================================

@app.route('/eventos/')
def lista_eventos():
    """Lista todos los eventos con su progreso"""
    eventos = query("SELECT * FROM eventos ORDER BY id")
    eventos_con_progreso = [obtener_evento_con_progreso(e) for e in eventos]
    return render_template('lista_eventos.html',
        titulo='Eventos',
        eventos=eventos_con_progreso
    )

# ==============================================================
# RUTAS HTML - Crear evento (CRUD - Create)
# ==============================================================

@app.route('/eventos/nuevo/', methods=['GET', 'POST'])
def crear_evento():
    """Formulario para crear un nuevo evento"""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '')
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        ubicacion = request.form.get('ubicacion', '')
        tipo_evento = request.form.get('tipo_evento')
        estado = request.form.get('estado', 'PLANEADO')
        
        # Validación: nombre obligatorio
        if not nombre:
            return render_template('form_evento.html',
                titulo='Crear Evento',
                accion='Crear',
                error='El campo nombre es obligatorio.',
                evento=request.form
            )
        
        # Validación: fechas coherentes
        if fecha_fin and fecha_inicio and fecha_fin < fecha_inicio:
            return render_template('form_evento.html',
                titulo='Crear Evento',
                accion='Crear',
                error='La fecha de fin no puede ser anterior a la fecha de inicio.',
                evento=request.form
            )
        
        execute(
            """INSERT INTO eventos (nombre, descripcion, fecha_inicio, fecha_fin, 
               ubicacion, tipo_evento, estado) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (nombre, descripcion, fecha_inicio, fecha_fin, ubicacion, tipo_evento, estado)
        )
        return render_template('form_evento.html',
            titulo='Crear Evento',
            accion='Crear',
            exito='Evento creado correctamente.',
            evento={}
        )
    
    return render_template('form_evento.html',
        titulo='Crear Evento',
        accion='Crear',
        evento={}
    )

# ==============================================================
# RUTAS HTML - Editar evento (CRUD - Update)
# ==============================================================

@app.route('/eventos/<int:id>/editar/', methods=['GET', 'POST'])
def editar_evento(id):
    """Formulario para editar un evento existente"""
    evento = query("SELECT * FROM eventos WHERE id = %s", (id,), one=True)
    if evento is None:
        abort(404)
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '')
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        ubicacion = request.form.get('ubicacion', '')
        tipo_evento = request.form.get('tipo_evento')
        estado = request.form.get('estado', 'PLANEADO')
        
        # Validación: nombre obligatorio
        if not nombre:
            evento_actual = dict(evento)
            evento_actual.update(request.form)
            return render_template('form_evento.html',
                titulo='Editar Evento',
                accion='Editar',
                evento=evento_actual,
                error='El campo nombre es obligatorio.'
            )
        
        # Validación: fechas coherentes
        if fecha_fin and fecha_inicio and fecha_fin < fecha_inicio:
            evento_actual = dict(evento)
            evento_actual.update(request.form)
            return render_template('form_evento.html',
                titulo='Editar Evento',
                accion='Editar',
                evento=evento_actual,
                error='La fecha de fin no puede ser anterior a la fecha de inicio.'
            )
        
        execute(
            """UPDATE eventos SET nombre=%s, descripcion=%s, fecha_inicio=%s, 
               fecha_fin=%s, ubicacion=%s, tipo_evento=%s, estado=%s 
               WHERE id=%s""",
            (nombre, descripcion, fecha_inicio, fecha_fin, ubicacion, tipo_evento, estado, id)
        )
        return render_template('form_evento.html',
            titulo='Editar Evento',
            accion='Editar',
            evento=request.form,
            exito='Evento actualizado correctamente.'
        )
    
    return render_template('form_evento.html',
        titulo='Editar Evento',
        accion='Editar',
        evento=evento
    )

# ==============================================================
# RUTAS HTML - Eliminar evento (CRUD - Delete)
# ==============================================================

@app.route('/eventos/<int:id>/eliminar/', methods=['GET', 'POST'])
def eliminar_evento(id):
    """Página de confirmación para eliminar un evento"""
    evento = query("SELECT * FROM eventos WHERE id = %s", (id,), one=True)
    if evento is None:
        abort(404)
    
    if request.method == 'POST':
        execute("DELETE FROM eventos WHERE id = %s", (id,))
        return render_template('confirmar_eliminar.html',
            titulo='Evento Eliminado',
            mensaje=f'El evento "{evento["nombre"]}" fue eliminado correctamente.',
            tipo='evento',
            eliminado=True
        )
    
    tareas = query("SELECT * FROM tareas WHERE evento_id = %s", (id,))
    return render_template('confirmar_eliminar.html',
        titulo='Eliminar Evento',
        evento=evento,
        tareas=tareas,
        tipo='evento',
        eliminado=False
    )

# ==============================================================
# RUTAS HTML - Filtrar eventos por tipo
# ==============================================================

@app.route('/eventos/filtro/')
def filtrar_eventos():
    """Filtrar eventos por tipo o estado"""
    tipo = request.args.get('tipo', '')
    estado = request.args.get('estado', '')
    
    sql = "SELECT * FROM eventos WHERE 1=1"
    params = []
    
    if tipo:
        sql += " AND tipo_evento = %s"
        params.append(tipo)
    if estado:
        sql += " AND estado = %s"
        params.append(estado)
    
    sql += " ORDER BY id"
    
    eventos = query(sql, tuple(params))
    eventos_con_progreso = [obtener_evento_con_progreso(e) for e in eventos]
    
    return render_template('lista_eventos.html',
        titulo='Eventos Filtrados',
        eventos=eventos_con_progreso,
        filtro_activo=True,
        tipo_filtro=tipo,
        estado_filtro=estado
    )

# ==============================================================
# RUTAS HTML - Detalle del evento
# ==============================================================

@app.route('/eventos/<int:id>/')
def detalle_evento(id):
    """Detalle completo de un evento con sus tareas"""
    evento = query("SELECT * FROM eventos WHERE id = %s", (id,), one=True)
    if evento is None:
        abort(404)
    
    tareas = query("SELECT * FROM tareas WHERE evento_id = %s", (id,))
    porcentaje = calcular_progreso(id)
    
    evento_con_progreso = dict(evento)
    evento_con_progreso['porcentaje_avance'] = porcentaje
    
    return render_template('detalle_evento.html',
        titulo=f'Detalle: {evento["nombre"]}',
        evento=evento_con_progreso,
        tareas=tareas
    )

# ==============================================================
# RUTAS HTML - Crear tarea
# ==============================================================

@app.route('/eventos/<int:evento_id>/tareas/nueva/', methods=['GET', 'POST'])
def crear_tarea(evento_id):
    """Formulario para crear una nueva tarea"""
    evento = query("SELECT * FROM eventos WHERE id = %s", (evento_id,), one=True)
    if evento is None:
        abort(404)
    
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '')
        encargado = request.form.get('encargado', '').strip()
        fecha_limite = request.form.get('fecha_limite')
        
        # Validación: título obligatorio
        if not titulo:
            return render_template('form_tarea.html',
                titulo='Crear Tarea',
                accion='Crear',
                evento=evento,
                tarea=request.form,
                error='El campo título es obligatorio.'
            )
        
        # Validación: encargado obligatorio
        if not encargado:
            return render_template('form_tarea.html',
                titulo='Crear Tarea',
                accion='Crear',
                evento=evento,
                tarea=request.form,
                error='El campo encargado es obligatorio.'
            )
        
        # Validación: fecha límite dentro del evento
        if fecha_limite and fecha_limite > str(evento['fecha_fin']):
            return render_template('form_tarea.html',
                titulo='Crear Tarea',
                accion='Crear',
                evento=evento,
                tarea=request.form,
                error=f'La fecha límite no puede ser posterior a {evento["fecha_fin"]}.'
            )
        
        execute(
            """INSERT INTO tareas (titulo, descripcion, evento_id, encargado, fecha_limite, completada) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (titulo, descripcion, evento_id, encargado, fecha_limite, False)
        )
        return render_template('form_tarea.html',
            titulo='Crear Tarea',
            accion='Crear',
            evento=evento,
            tarea={},
            exito='Tarea creada correctamente.'
        )
    
    return render_template('form_tarea.html',
        titulo='Crear Tarea',
        accion='Crear',
        evento=evento,
        tarea={}
    )

# ==============================================================
# RUTAS HTML - Editar tarea
# ==============================================================

@app.route('/tareas/<int:id>/editar/', methods=['GET', 'POST'])
def editar_tarea(id):
    """Formulario para editar una tarea"""
    tarea = query("SELECT * FROM tareas WHERE id = %s", (id,), one=True)
    if tarea is None:
        abort(404)
    
    evento = query("SELECT * FROM eventos WHERE id = %s", (tarea['evento_id'],), one=True)
    
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '')
        encargado = request.form.get('encargado', '').strip()
        fecha_limite = request.form.get('fecha_limite')
        completada = 1 if request.form.get('completada') else 0
        
        # Validación: título obligatorio
        if not titulo:
            tarea_actual = dict(tarea)
            tarea_actual.update(request.form)
            return render_template('form_tarea.html',
                titulo='Editar Tarea',
                accion='Editar',
                evento=evento,
                tarea=tarea_actual,
                error='El campo título es obligatorio.'
            )
        
        # Validación: encargado obligatorio
        if not encargado:
            tarea_actual = dict(tarea)
            tarea_actual.update(request.form)
            return render_template('form_tarea.html',
                titulo='Editar Tarea',
                accion='Editar',
                evento=evento,
                tarea=tarea_actual,
                error='El campo encargado es obligatorio.'
            )
        
        # Validación: fecha límite dentro del evento
        if fecha_limite and fecha_limite > str(evento['fecha_fin']):
            tarea_actual = dict(tarea)
            tarea_actual.update(request.form)
            return render_template('form_tarea.html',
                titulo='Editar Tarea',
                accion='Editar',
                evento=evento,
                tarea=tarea_actual,
                error=f'La fecha límite no puede ser posterior a {evento["fecha_fin"]}.'
            )
        
        execute(
            """UPDATE tareas SET titulo=%s, descripcion=%s, encargado=%s, 
               fecha_limite=%s, completada=%s WHERE id=%s""",
            (titulo, descripcion, encargado, fecha_limite, completada, id)
        )
        return render_template('form_tarea.html',
            titulo='Editar Tarea',
            accion='Editar',
            evento=evento,
            tarea=request.form,
            exito='Tarea actualizada correctamente.'
        )
    
    return render_template('form_tarea.html',
        titulo='Editar Tarea',
        accion='Editar',
        evento=evento,
        tarea=tarea
    )

# ==============================================================
# RUTAS HTML - Eliminar tarea
# ==============================================================

@app.route('/tareas/<int:id>/eliminar/', methods=['GET', 'POST'])
def eliminar_tarea(id):
    """Página de confirmación para eliminar una tarea"""
    tarea = query("SELECT * FROM tareas WHERE id = %s", (id,), one=True)
    if tarea is None:
        abort(404)
    
    evento = query("SELECT * FROM eventos WHERE id = %s", (tarea['evento_id'],), one=True)
    
    if request.method == 'POST':
        execute("DELETE FROM tareas WHERE id = %s", (id,))
        return render_template('confirmar_eliminar.html',
            titulo='Tarea Eliminada',
            mensaje=f'La tarea "{tarea["titulo"]}" fue eliminada correctamente.',
            tipo='tarea',
            eliminado=True,
            evento=evento
        )
    
    return render_template('confirmar_eliminar.html',
        titulo='Eliminar Tarea',
        tipo='tarea',
        eliminado=False,
        tarea=tarea,
        evento=evento
    )

# ==============================================================
# RUTAS API - GET /api/eventos/
# ==============================================================

@app.route('/api/eventos/')
def api_lista_eventos():
    """API: Listar todos los eventos con porcentaje de avance"""
    eventos = query("SELECT * FROM eventos")
    eventos_con_progreso = [obtener_evento_con_progreso(e) for e in eventos]
    return jsonify({
        'total': len(eventos_con_progreso),
        'eventos': eventos_con_progreso
    })

# ==============================================================
# RUTAS API - GET /api/eventos/<id>/
# ==============================================================

@app.route('/api/eventos/<int:id>/')
def api_detalle_evento(id):
    """API: Obtener un evento específico con sus tareas y porcentaje"""
    evento = query("SELECT * FROM eventos WHERE id = %s", (id,), one=True)
    if evento is None:
        return jsonify({'error': 'Evento no encontrado', 'id': id}), 404
    
    tareas = query("SELECT * FROM tareas WHERE evento_id = %s", (id,))
    porcentaje = calcular_progreso(id)
    
    resultado = dict(evento)
    resultado['porcentaje_avance'] = porcentaje
    resultado['tareas'] = tareas
    
    return jsonify(resultado)

# ==============================================================
# RUTAS API - POST /api/eventos/ (Crear evento)
# ==============================================================

@app.route('/api/eventos/', methods=['POST'])
def api_crear_evento():
    """API: Crear un nuevo evento"""
    datos = request.get_json()
    
    if not datos:
        return jsonify({'error': 'El cuerpo debe ser JSON'}), 400
    
    nombre = datos.get('nombre', '').strip()
    if not nombre:
        return jsonify({'error': 'El campo nombre es obligatorio'}), 400
    
    fecha_inicio = datos.get('fecha_inicio')
    fecha_fin = datos.get('fecha_fin')
    
    # Validación: fechas coherentes
    if fecha_fin and fecha_inicio and fecha_fin < fecha_inicio:
        return jsonify({'error': 'La fecha de fin no puede ser anterior a la fecha de inicio'}), 400
    
    tipo_evento = datos.get('tipo_evento')
    tipos_validos = ['MISIONES', 'FAMILIAS', 'ANIVERSARIO', 'DIA_ESPECIAL', 'RETIRO', 'SOLIDARIO', 'OTRO']
    if tipo_evento not in tipos_validos:
        return jsonify({'error': f'Tipo de evento inválido. Valores: {tipos_validos}'}), 400
    
    estado = datos.get('estado', 'PLANEADO')
    estados_validos = ['PLANEADO', 'EN_PREPARACION', 'EN_CURSO', 'FINALIZADO', 'CANCELADO']
    if estado not in estados_validos:
        return jsonify({'error': f'Estado inválido. Valores: {estados_validos}'}), 400
    
    nuevo_id = execute(
        """INSERT INTO eventos (nombre, descripcion, fecha_inicio, fecha_fin, 
           ubicacion, tipo_evento, estado) 
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (nombre, datos.get('descripcion', ''), fecha_inicio, fecha_fin, 
         datos.get('ubicacion', ''), tipo_evento, estado)
    )
    
    nuevo = query("SELECT * FROM eventos WHERE id = %s", (nuevo_id,), one=True)
    return jsonify({
        'mensaje': 'Evento creado correctamente',
        'evento': nuevo
    }), 201

# ==============================================================
# RUTAS API - PUT /api/eventos/<id>/ (Actualizar evento)
# ==============================================================

@app.route('/api/eventos/<int:id>/', methods=['PUT'])
def api_actualizar_evento(id):
    """API: Actualizar un evento existente"""
    evento = query("SELECT * FROM eventos WHERE id = %s", (id,), one=True)
    if evento is None:
        return jsonify({'error': 'Evento no encontrado', 'id': id}), 404
    
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'El cuerpo debe ser JSON'}), 400
    
    nombre = datos.get('nombre', evento['nombre']).strip()
    if not nombre:
        return jsonify({'error': 'El campo nombre no puede quedar vacío'}), 400
    
    fecha_inicio = datos.get('fecha_inicio', evento['fecha_inicio'])
    fecha_fin = datos.get('fecha_fin', evento['fecha_fin'])
    
    if fecha_fin and fecha_inicio and fecha_fin < fecha_inicio:
        return jsonify({'error': 'La fecha de fin no puede ser anterior a la fecha de inicio'}), 400
    
    tipo_evento = datos.get('tipo_evento', evento['tipo_evento'])
    tipos_validos = ['MISIONES', 'FAMILIAS', 'ANIVERSARIO', 'DIA_ESPECIAL', 'RETIRO', 'SOLIDARIO', 'OTRO']
    if tipo_evento not in tipos_validos:
        return jsonify({'error': 'Tipo de evento inválido'}), 400
    
    estado = datos.get('estado', evento['estado'])
    estados_validos = ['PLANEADO', 'EN_PREPARACION', 'EN_CURSO', 'FINALIZADO', 'CANCELADO']
    if estado not in estados_validos:
        return jsonify({'error': 'Estado inválido'}), 400
    
    execute(
        """UPDATE eventos SET nombre=%s, descripcion=%s, fecha_inicio=%s, 
           fecha_fin=%s, ubicacion=%s, tipo_evento=%s, estado=%s 
           WHERE id=%s""",
        (nombre, datos.get('descripcion', evento['descripcion']), 
         fecha_inicio, fecha_fin, datos.get('ubicacion', evento['ubicacion']), 
         tipo_evento, estado, id)
    )
    
    actualizado = query("SELECT * FROM eventos WHERE id = %s", (id,), one=True)
    return jsonify({
        'mensaje': 'Evento actualizado correctamente',
        'evento': actualizado
    })

# ==============================================================
# RUTAS API - DELETE /api/eventos/<id>/ (Eliminar evento)
# ==============================================================

@app.route('/api/eventos/<int:id>/', methods=['DELETE'])
def api_eliminar_evento(id):
    """API: Eliminar un evento"""
    evento = query("SELECT * FROM eventos WHERE id = %s", (id,), one=True)
    if evento is None:
        return jsonify({'error': 'Evento no encontrado', 'id': id}), 404
    
    execute("DELETE FROM eventos WHERE id = %s", (id,))
    return jsonify({
        'mensaje': f'Evento "{evento["nombre"]}" eliminado correctamente',
        'id': id
    })

# ==============================================================
# RUTAS API - GET /api/tareas/
# ==============================================================

@app.route('/api/tareas/')
def api_lista_tareas():
    """API: Listar todas las tareas"""
    tareas = query("SELECT * FROM tareas")
    return jsonify({
        'total': len(tareas),
        'tareas': tareas
    })

# ==============================================================
# RUTAS API - POST /api/tareas/ (Crear tarea)
# ==============================================================

@app.route('/api/tareas/', methods=['POST'])
def api_crear_tarea():
    """API: Crear una nueva tarea"""
    datos = request.get_json()
    
    if not datos:
        return jsonify({'error': 'El cuerpo debe ser JSON'}), 400
    
    titulo = datos.get('titulo', '').strip()
    if not titulo:
        return jsonify({'error': 'El campo título es obligatorio'}), 400
    
    evento_id = datos.get('evento_id')
    evento = query("SELECT * FROM eventos WHERE id = %s", (evento_id,), one=True)
    if evento is None:
        return jsonify({'error': 'El evento asociado no existe'}), 400
    
    encargado = datos.get('encargado', '').strip()
    if not encargado:
        return jsonify({'error': 'El campo encargado es obligatorio'}), 400
    
    fecha_limite = datos.get('fecha_limite')
    if fecha_limite and fecha_limite > str(evento['fecha_fin']):
        return jsonify({'error': f'La fecha límite no puede ser posterior a {evento["fecha_fin"]}'}), 400
    
    nuevo_id = execute(
        """INSERT INTO tareas (titulo, descripcion, evento_id, encargado, fecha_limite, completada) 
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (titulo, datos.get('descripcion', ''), evento_id, encargado, fecha_limite, 
         datos.get('completada', False))
    )
    
    nueva = query("SELECT * FROM tareas WHERE id = %s", (nuevo_id,), one=True)
    return jsonify({
        'mensaje': 'Tarea creada correctamente',
        'tarea': nueva
    }), 201

# ==============================================================
# RUTAS API - PUT /api/tareas/<id>/ (Actualizar tarea)
# ==============================================================

@app.route('/api/tareas/<int:id>/', methods=['PUT'])
def api_actualizar_tarea(id):
    """API: Actualizar una tarea"""
    tarea = query("SELECT * FROM tareas WHERE id = %s", (id,), one=True)
    if tarea is None:
        return jsonify({'error': 'Tarea no encontrada', 'id': id}), 404
    
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'El cuerpo debe ser JSON'}), 400
    
    titulo = datos.get('titulo', tarea['titulo']).strip()
    if not titulo:
        return jsonify({'error': 'El campo título no puede quedar vacío'}), 400
    
    encargado = datos.get('encargado', tarea['encargado']).strip()
    if not encargado:
        return jsonify({'error': 'El campo encargado no puede quedar vacío'}), 400
    
    evento = query("SELECT * FROM eventos WHERE id = %s", (tarea['evento_id'],), one=True)
    fecha_limite = datos.get('fecha_limite', tarea['fecha_limite'])
    
    if fecha_limite and fecha_limite > str(evento['fecha_fin']):
        return jsonify({'error': f'La fecha límite no puede ser posterior a {evento["fecha_fin"]}'}), 400
    
    execute(
        """UPDATE tareas SET titulo=%s, descripcion=%s, encargado=%s, 
           fecha_limite=%s, completada=%s WHERE id=%s""",
        (titulo, datos.get('descripcion', tarea['descripcion']), 
         encargado, fecha_limite, datos.get('completada', tarea['completada']), id)
    )
    
    actualizada = query("SELECT * FROM tareas WHERE id = %s", (id,), one=True)
    return jsonify({
        'mensaje': 'Tarea actualizada correctamente',
        'tarea': actualizada
    })

# ==============================================================
# RUTAS API - DELETE /api/tareas/<id>/ (Eliminar tarea)
# ==============================================================

@app.route('/api/tareas/<int:id>/', methods=['DELETE'])
def api_eliminar_tarea(id):
    """API: Eliminar una tarea"""
    tarea = query("SELECT * FROM tareas WHERE id = %s", (id,), one=True)
    if tarea is None:
        return jsonify({'error': 'Tarea no encontrada', 'id': id}), 404
    
    execute("DELETE FROM tareas WHERE id = %s", (id,))
    return jsonify({
        'mensaje': f'Tarea "{tarea["titulo"]}" eliminada correctamente',
        'id': id
    })

# ==============================================================
# RUTAS API - GET /api/resumen/ (Estadísticas)
# ==============================================================

@app.route('/api/resumen/')
def api_resumen():
    """API: Estadísticas generales del sistema"""
    eventos = query("SELECT * FROM eventos")
    tareas = query("SELECT * FROM tareas")
    
    tareas_completadas = sum(1 for t in tareas if t['completada'])
    
    # Eventos por tipo
    eventos_por_tipo = {}
    for e in eventos:
        eventos_por_tipo[e['tipo_evento']] = eventos_por_tipo.get(e['tipo_evento'], 0) + 1
    
    # Eventos por estado
    eventos_por_estado = {}
    for e in eventos:
        eventos_por_estado[e['estado']] = eventos_por_estado.get(e['estado'], 0) + 1
    
    return jsonify({
        'total_eventos': len(eventos),
        'total_tareas': len(tareas),
        'tareas_completadas': tareas_completadas,
        'tareas_pendientes': len(tareas) - tareas_completadas,
        'eventos_por_tipo': eventos_por_tipo,
        'eventos_por_estado': eventos_por_estado
    })

# ==============================================================
# RUTAS API - GET /api/eventos/filtro/ (Filtros)
# ==============================================================

@app.route('/api/eventos/filtro/')
def api_filtrar_eventos():
    """API: Filtrar eventos por tipo o estado"""
    tipo = request.args.get('tipo', '')
    estado = request.args.get('estado', '')
    
    sql = "SELECT * FROM eventos WHERE 1=1"
    params = []
    
    if tipo:
        sql += " AND tipo_evento = %s"
        params.append(tipo)
    if estado:
        sql += " AND estado = %s"
        params.append(estado)
    
    sql += " ORDER BY id"
    
    eventos = query(sql, tuple(params))
    eventos_con_progreso = [obtener_evento_con_progreso(e) for e in eventos]
    
    return jsonify({
        'total': len(eventos_con_progreso),
        'filtros': {'tipo': tipo, 'estado': estado},
        'eventos': eventos_con_progreso
    })

# ==============================================================
# MANEJO DE ERRORES
# ==============================================================

@app.errorhandler(404)
def pagina_no_encontrada(e):
    """Página 404 personalizada"""
    return render_template('404.html', titulo='Página no encontrada'), 404

# ==============================================================
# INICIO DEL SERVIDOR
# ==============================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)