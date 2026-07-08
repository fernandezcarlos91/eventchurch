# app.py - EventChurch para PythonAnywhere con SQLite

from flask import Flask, render_template, jsonify, request, abort
import sqlite3
import os

app = Flask(__name__)

# ==============================================================
# CONFIGURACIÓN DE BASE DE DATOS (SQLite)
# ==============================================================

DB_PATH = os.path.join(os.path.dirname(__file__), 'eventchurch.db')

def get_db_connection():
    """Obtiene una conexión a la base de datos SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def query(sql, params=(), one=False):
    """Ejecuta SELECT y retorna filas como diccionarios"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    
    if one:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if result:
        if one:
            return dict(result)
        else:
            return [dict(row) for row in result]
    return None if one else []

def execute(sql, params=()):
    """Ejecuta INSERT, UPDATE o DELETE"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    lastrowid = cursor.lastrowid
    cursor.close()
    conn.close()
    return lastrowid

# ==============================================================
# FUNCIÓN PARA CREAR TABLAS AUTOMÁTICAMENTE
# ==============================================================

def crear_tablas():
    """Crea las tablas si no existen"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Crear tabla eventos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            ubicacion TEXT,
            estado TEXT DEFAULT 'PLANEADO',
            tipo_evento TEXT NOT NULL
        )
    """)
    
    # Crear tabla tareas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            evento_id INTEGER NOT NULL,
            encargado TEXT NOT NULL,
            fecha_limite TEXT NOT NULL,
            completada INTEGER DEFAULT 0,
            FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    
    # Verificar si hay datos de prueba
    cursor.execute("SELECT COUNT(*) as total FROM eventos")
    count = cursor.fetchone()
    
    if count[0] == 0:
        # Insertar datos de prueba
        cursor.execute("""
            INSERT INTO eventos (nombre, descripcion, fecha_inicio, fecha_fin, ubicacion, tipo_evento, estado)
            VALUES 
                ('Conferencia de Misiones 2026', 'Conferencia anual de misiones con invitados especiales', '2026-08-15', '2026-08-17', 'Templo Central', 'MISIONES', 'PLANEADO'),
                ('Celebración 15° Aniversario', 'Celebración del 15 aniversario de la iglesia', '2026-05-20', '2026-05-20', 'Templo Central', 'ANIVERSARIO', 'EN_PREPARACION'),
                ('Retiro de Familias', 'Retiro espiritual para familias', '2026-07-10', '2026-07-12', 'Centro de Retiros El Shaddai', 'FAMILIAS', 'PLANEADO')
        """)
        
        evento_id = cursor.lastrowid - 2  # ID del primer evento
        
        cursor.execute("""
            INSERT INTO tareas (titulo, descripcion, evento_id, encargado, fecha_limite, completada)
            VALUES 
                ('Preparar lista de invitados', 'Hacer lista de invitados especiales', 1, 'María Pérez', '2026-07-15', 0),
                ('Coordinar música y alabanza', 'Organizar el grupo de alabanza', 1, 'Pedro González', '2026-08-01', 0),
                ('Organizar logística de alimentos', 'Coordinar comida para los asistentes', 1, 'Juan López', '2026-08-10', 0)
        """)
        
        conn.commit()
        print("✅ Tablas creadas y datos de prueba insertados")
    else:
        print("✅ Tablas ya existen")
    
    cursor.close()
    conn.close()

# Crear tablas al iniciar
crear_tablas()

# ==============================================================
# FUNCIONES AUXILIARES - Lógica de negocio
# ==============================================================

def calcular_progreso(evento_id):
    """Calcula el porcentaje de avance de un evento"""
    tareas = query(
        "SELECT COUNT(*) as total, SUM(completada) as completadas FROM tareas WHERE evento_id = ?",
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
# RUTAS HTML - Lista de eventos
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
# RUTAS HTML - Detalle de evento
# ==============================================================

@app.route('/eventos/<int:id>/')
def detalle_evento(id):
    """Detalle completo de un evento con sus tareas"""
    evento = query("SELECT * FROM eventos WHERE id = ?", (id,), one=True)
    if evento is None:
        abort(404)
    
    tareas = query("SELECT * FROM tareas WHERE evento_id = ?", (id,))
    porcentaje = calcular_progreso(id)
    
    evento_con_progreso = dict(evento)
    evento_con_progreso['porcentaje_avance'] = porcentaje
    
    return render_template('detalle_evento.html',
        titulo=f'Detalle: {evento["nombre"]}',
        evento=evento_con_progreso,
        tareas=tareas
    )

# ==============================================================
# RUTAS HTML - Lista de todas las tareas
# ==============================================================

@app.route('/tareas/')
def lista_tareas():
    """Lista todas las tareas con información del evento asociado"""
    tareas = query("""
        SELECT t.*, e.nombre as evento_nombre 
        FROM tareas t 
        LEFT JOIN eventos e ON t.evento_id = e.id 
        ORDER BY t.completada ASC, t.fecha_limite ASC
    """)
    
    return render_template('lista_tareas.html',
        titulo='Tareas',
        tareas=tareas
    )

# ==============================================================
# RUTAS HTML - Detalle de tarea
# ==============================================================

@app.route('/tareas/<int:id>/')
def detalle_tarea(id):
    """Detalle completo de una tarea"""
    tarea = query("SELECT * FROM tareas WHERE id = ?", (id,), one=True)
    if tarea is None:
        abort(404)
    
    evento = query("SELECT * FROM eventos WHERE id = ?", (tarea['evento_id'],), one=True)
    
    return render_template('detalle_tarea.html',
        titulo=f'Detalle: {tarea["titulo"]}',
        tarea=tarea,
        evento=evento
    )

# ==============================================================
# RUTAS HTML - Crear evento
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
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
# RUTAS HTML - Editar evento
# ==============================================================

@app.route('/eventos/<int:id>/editar/', methods=['GET', 'POST'])
def editar_evento(id):
    """Formulario para editar un evento existente"""
    evento = query("SELECT * FROM eventos WHERE id = ?", (id,), one=True)
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
            """UPDATE eventos SET nombre=?, descripcion=?, fecha_inicio=?, 
               fecha_fin=?, ubicacion=?, tipo_evento=?, estado=? 
               WHERE id=?""",
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
# RUTAS HTML - Eliminar evento
# ==============================================================

@app.route('/eventos/<int:id>/eliminar/', methods=['GET', 'POST'])
def eliminar_evento(id):
    """Página de confirmación para eliminar un evento"""
    evento = query("SELECT * FROM eventos WHERE id = ?", (id,), one=True)
    if evento is None:
        abort(404)
    
    if request.method == 'POST':
        execute("DELETE FROM eventos WHERE id = ?", (id,))
        return render_template('confirmar_eliminar.html',
            titulo='Evento Eliminado',
            mensaje=f'El evento "{evento["nombre"]}" fue eliminado correctamente.',
            tipo='evento',
            eliminado=True
        )
    
    tareas = query("SELECT * FROM tareas WHERE evento_id = ?", (id,))
    return render_template('confirmar_eliminar.html',
        titulo='Eliminar Evento',
        evento=evento,
        tareas=tareas,
        tipo='evento',
        eliminado=False
    )

# ==============================================================
# RUTAS HTML - Filtrar eventos
# ==============================================================

@app.route('/eventos/filtro/')
def filtrar_eventos():
    """Filtrar eventos por tipo o estado"""
    tipo = request.args.get('tipo', '')
    estado = request.args.get('estado', '')
    
    sql = "SELECT * FROM eventos WHERE 1=1"
    params = []
    
    if tipo:
        sql += " AND tipo_evento = ?"
        params.append(tipo)
    if estado:
        sql += " AND estado = ?"
        params.append(estado)
    
    sql += " ORDER BY id"
    
    eventos = query(sql, tuple(params))
    eventos_con_progreso = [obtener_evento_con_progreso(e) for e in eventos]
    
    return render_template('lista_eventos.html',
        titulo='Eventos Filtrados',
        eventos=eventos_con_progreso
    )

# ==============================================================
# RUTAS HTML - Crear tarea
# ==============================================================

@app.route('/eventos/<int:evento_id>/tareas/nueva/', methods=['GET', 'POST'])
def crear_tarea(evento_id):
    """Formulario para crear una nueva tarea"""
    evento = query("SELECT * FROM eventos WHERE id = ?", (evento_id,), one=True)
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
               VALUES (?, ?, ?, ?, ?, ?)""",
            (titulo, descripcion, evento_id, encargado, fecha_limite, 0)
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
    tarea = query("SELECT * FROM tareas WHERE id = ?", (id,), one=True)
    if tarea is None:
        abort(404)
    
    evento = query("SELECT * FROM eventos WHERE id = ?", (tarea['evento_id'],), one=True)
    
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
            """UPDATE tareas SET titulo=?, descripcion=?, encargado=?, 
               fecha_limite=?, completada=? WHERE id=?""",
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
    tarea = query("SELECT * FROM tareas WHERE id = ?", (id,), one=True)
    if tarea is None:
        abort(404)
    
    evento = query("SELECT * FROM eventos WHERE id = ?", (tarea['evento_id'],), one=True)
    
    if request.method == 'POST':
        execute("DELETE FROM tareas WHERE id = ?", (id,))
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
    evento = query("SELECT * FROM eventos WHERE id = ?", (id,), one=True)
    if evento is None:
        return jsonify({'error': 'Evento no encontrado', 'id': id}), 404
    
    tareas = query("SELECT * FROM tareas WHERE evento_id = ?", (id,))
    porcentaje = calcular_progreso(id)
    
    resultado = dict(evento)
    resultado['porcentaje_avance'] = porcentaje
    resultado['tareas'] = tareas
    
    return jsonify(resultado)

# ==============================================================
# RUTAS API - POST /api/eventos/
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
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (nombre, datos.get('descripcion', ''), fecha_inicio, fecha_fin, 
         datos.get('ubicacion', ''), tipo_evento, estado)
    )
    
    nuevo = query("SELECT * FROM eventos WHERE id = ?", (nuevo_id,), one=True)
    return jsonify({
        'mensaje': 'Evento creado correctamente',
        'evento': nuevo
    }), 201

# ==============================================================
# RUTAS API - PUT /api/eventos/<id>/
# ==============================================================

@app.route('/api/eventos/<int:id>/', methods=['PUT'])
def api_actualizar_evento(id):
    """API: Actualizar un evento existente"""
    evento = query("SELECT * FROM eventos WHERE id = ?", (id,), one=True)
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
        """UPDATE eventos SET nombre=?, descripcion=?, fecha_inicio=?, 
           fecha_fin=?, ubicacion=?, tipo_evento=?, estado=? 
           WHERE id=?""",
        (nombre, datos.get('descripcion', evento['descripcion']), 
         fecha_inicio, fecha_fin, datos.get('ubicacion', evento['ubicacion']), 
         tipo_evento, estado, id)
    )
    
    actualizado = query("SELECT * FROM eventos WHERE id = ?", (id,), one=True)
    return jsonify({
        'mensaje': 'Evento actualizado correctamente',
        'evento': actualizado
    })

# ==============================================================
# RUTAS API - DELETE /api/eventos/<id>/
# ==============================================================

@app.route('/api/eventos/<int:id>/', methods=['DELETE'])
def api_eliminar_evento(id):
    """API: Eliminar un evento"""
    evento = query("SELECT * FROM eventos WHERE id = ?", (id,), one=True)
    if evento is None:
        return jsonify({'error': 'Evento no encontrado', 'id': id}), 404
    
    execute("DELETE FROM eventos WHERE id = ?", (id,))
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
# RUTAS API - GET /api/tareas/<id>/
# ==============================================================

@app.route('/api/tareas/<int:id>/')
def api_detalle_tarea(id):
    """API: Obtener una tarea específica"""
    tarea = query("SELECT * FROM tareas WHERE id = ?", (id,), one=True)
    if tarea is None:
        return jsonify({'error': 'Tarea no encontrada', 'id': id}), 404
    
    evento = query("SELECT * FROM eventos WHERE id = ?", (tarea['evento_id'],), one=True)
    resultado = dict(tarea)
    resultado['evento_nombre'] = evento['nombre'] if evento else None
    
    return jsonify(resultado)

# ==============================================================
# RUTAS API - POST /api/tareas/
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
    evento = query("SELECT * FROM eventos WHERE id = ?", (evento_id,), one=True)
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
           VALUES (?, ?, ?, ?, ?, ?)""",
        (titulo, datos.get('descripcion', ''), evento_id, encargado, fecha_limite, 
         datos.get('completada', 0))
    )
    
    nueva = query("SELECT * FROM tareas WHERE id = ?", (nuevo_id,), one=True)
    return jsonify({
        'mensaje': 'Tarea creada correctamente',
        'tarea': nueva
    }), 201

# ==============================================================
# RUTAS API - PUT /api/tareas/<id>/
# ==============================================================

@app.route('/api/tareas/<int:id>/', methods=['PUT'])
def api_actualizar_tarea(id):
    """API: Actualizar una tarea"""
    tarea = query("SELECT * FROM tareas WHERE id = ?", (id,), one=True)
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
    
    evento = query("SELECT * FROM eventos WHERE id = ?", (tarea['evento_id'],), one=True)
    fecha_limite = datos.get('fecha_limite', tarea['fecha_limite'])
    
    if fecha_limite and fecha_limite > str(evento['fecha_fin']):
        return jsonify({'error': f'La fecha límite no puede ser posterior a {evento["fecha_fin"]}'}), 400
    
    execute(
        """UPDATE tareas SET titulo=?, descripcion=?, encargado=?, 
           fecha_limite=?, completada=? WHERE id=?""",
        (titulo, datos.get('descripcion', tarea['descripcion']), 
         encargado, fecha_limite, datos.get('completada', tarea['completada']), id)
    )
    
    actualizada = query("SELECT * FROM tareas WHERE id = ?", (id,), one=True)
    return jsonify({
        'mensaje': 'Tarea actualizada correctamente',
        'tarea': actualizada
    })

# ==============================================================
# RUTAS API - DELETE /api/tareas/<id>/
# ==============================================================

@app.route('/api/tareas/<int:id>/', methods=['DELETE'])
def api_eliminar_tarea(id):
    """API: Eliminar una tarea"""
    tarea = query("SELECT * FROM tareas WHERE id = ?", (id,), one=True)
    if tarea is None:
        return jsonify({'error': 'Tarea no encontrada', 'id': id}), 404
    
    execute("DELETE FROM tareas WHERE id = ?", (id,))
    return jsonify({
        'mensaje': f'Tarea "{tarea["titulo"]}" eliminada correctamente',
        'id': id
    })

# ==============================================================
# RUTAS API - GET /api/resumen/
# ==============================================================

@app.route('/api/resumen/')
def api_resumen():
    """API: Estadísticas generales del sistema"""
    eventos = query("SELECT * FROM eventos")
    tareas = query("SELECT * FROM tareas")
    
    tareas_completadas = sum(1 for t in tareas if t['completada'])
    
    eventos_por_tipo = {}
    for e in eventos:
        eventos_por_tipo[e['tipo_evento']] = eventos_por_tipo.get(e['tipo_evento'], 0) + 1
    
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
# RUTAS API - GET /api/eventos/filtro/
# ==============================================================

@app.route('/api/eventos/filtro/')
def api_filtrar_eventos():
    """API: Filtrar eventos por tipo o estado"""
    tipo = request.args.get('tipo', '')
    estado = request.args.get('estado', '')
    
    sql = "SELECT * FROM eventos WHERE 1=1"
    params = []
    
    if tipo:
        sql += " AND tipo_evento = ?"
        params.append(tipo)
    if estado:
        sql += " AND estado = ?"
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
# INICIO DEL SERVIDOR (PythonAnywhere usa la variable 'app')
# ==============================================================

# PythonAnywhere usa la variable 'app' como punto de entrada
# No se necesita app.run() en producción