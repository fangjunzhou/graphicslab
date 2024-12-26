#version 330

in vec3 in_vert;

uniform mat4 mat_M;
uniform mat4 mat_V;
uniform mat4 mat_P;
uniform mat4 mat_MV;
uniform mat4 mat_MVP;

void main() {
  vec4 proj_vert = mat_MVP * vec4(in_vert, 1);
  vec4 offset_vert = proj_vert - 0.0001 * vec4(0, 0, 1, 0);
  gl_Position = offset_vert;
}
