import 'package:intl/intl.dart';

class IncidentReport {
  const IncidentReport({
    required this.id, required this.reportId, required this.userId,
    required this.incidentType, required this.description, required this.latitude,
    required this.longitude, required this.createdAt, required this.status,
    this.receivedAt, this.resolvedAt, this.photoPath, this.locationAccuracy,
  });

  final String id, reportId, userId, incidentType, description, status;
  final double latitude, longitude;
  final DateTime createdAt;
  final DateTime? receivedAt, resolvedAt;
  final String? photoPath;
  final double? locationAccuracy;

  factory IncidentReport.fromMap(Map<String, dynamic> map) => IncidentReport(
    id: map['id'].toString(), reportId: map['report_id'] as String,
    userId: map['user_id'].toString(), incidentType: map['incident_type'] as String,
    description: map['description'] as String, latitude: (map['latitude'] as num).toDouble(),
    longitude: (map['longitude'] as num).toDouble(), createdAt: DateTime.parse(map['created_at'] as String),
    status: map['status'] as String, receivedAt: map['received_at'] == null ? null : DateTime.parse(map['received_at']),
    resolvedAt: map['resolved_at'] == null ? null : DateTime.parse(map['resolved_at']),
    photoPath: map['photo_path'] as String?, locationAccuracy: (map['location_accuracy'] as num?)?.toDouble(),
  );

  String get createdLabel => DateFormat('MMM d, y • h:mm a').format(createdAt.toLocal());
  String? get deliveryTime => receivedAt == null ? null : '${receivedAt!.difference(createdAt).inMilliseconds} ms';
}
