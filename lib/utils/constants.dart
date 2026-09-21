import 'package:flutter/material.dart';

const appName = 'iBantay';
const appSubtitle = 'Real-Time Community Incident Reporting';
const emergencyRed = Color(0xFFC62828);
const safetyNavy = Color(0xFF102A43);

const incidentTypes = <IncidentType>[
  IncidentType('Robbery', '🚨', Color(0xFF9C1C1C)),
  IncidentType('Theft', '🔒', Color(0xFF5D4037)),
  IncidentType('Shooting', '🔫', Color(0xFF4A5568)),
  IncidentType('Fire', '🔥', Color(0xFFEF6C00)),
  IncidentType('Accident', '🚗', Color(0xFF1565C0)),
  IncidentType('Medical Emergency', '🏥', Color(0xFF00897B)),
  IncidentType('Other Emergency', '⚠️', Color(0xFF6A1B9A)),
];

class IncidentType {
  const IncidentType(this.name, this.emoji, this.color);
  final String name;
  final String emoji;
  final Color color;
}

const reportStatuses = [
  'PENDING', 'RECEIVED', 'ASSIGNED', 'RESPONDER_ON_WAY', 'ARRIVED', 'RESOLVED', 'CANCELLED',
];

const activeStatuses = ['RECEIVED', 'ASSIGNED', 'RESPONDER_ON_WAY', 'ARRIVED'];
