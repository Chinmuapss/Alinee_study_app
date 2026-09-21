import 'dart:typed_data';
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/report.dart';
import 'supabase_service.dart';

class ReportService {
  final _client = SupabaseService.client;

  Future<String?> uploadPhoto(XFile? image, String userId) async {
    if (image == null) return null;
    final Uint8List bytes = await image.readAsBytes();
    final path = '$userId/${DateTime.now().millisecondsSinceEpoch}_${image.name}';
    await _client.storage.from('report-photos').uploadBinary(path, bytes, fileOptions: FileOptions(contentType: image.mimeType, upsert: false));
    return path;
  }

  Future<IncidentReport> submit({required String incidentType, required String description, required double latitude, required double longitude, required double accuracy, XFile? image}) async {
    final user = _client.auth.currentUser;
    if (user == null) throw const AuthException('Your session has expired. Please sign in again.');
    final photoPath = await uploadPhoto(image, user.id);
    final result = await _client.from('reports').insert({
      'user_id': user.id, 'incident_type': incidentType, 'description': description.trim(),
      'latitude': latitude, 'longitude': longitude, 'location_accuracy': accuracy, 'photo_path': photoPath,
    }).select().single();
    return IncidentReport.fromMap(result);
  }

  Future<List<IncidentReport>> mine() async {
    final data = await _client.from('reports').select().order('created_at', ascending: false);
    return data.map<IncidentReport>((e) => IncidentReport.fromMap(e)).toList();
  }
  Future<List<IncidentReport>> all() async {
    final data = await _client.from('reports').select().order('created_at', ascending: false);
    return data.map<IncidentReport>((e) => IncidentReport.fromMap(e)).toList();
  }
  Future<void> updateStatus(String id, String status) => _client.from('reports').update({'status': status}).eq('id', id);
  String photoUrl(String path) => _client.storage.from('report-photos').getPublicUrl(path);
}
